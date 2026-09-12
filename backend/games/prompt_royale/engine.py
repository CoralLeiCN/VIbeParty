from __future__ import annotations

import asyncio
import contextlib
import json
import secrets
import shutil
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.games.prompt_royale.config import TOPICS, RoyaleSettings
from backend.games.prompt_royale.helios import HeliosVideo
from backend.games.prompt_royale.providers import FixtureVideo, ProviderFailure, Topics
from backend.games.prompt_royale.validation import PromptValidator, normalized, rendered
from backend.shared.contracts import GameContext
from backend.shared.errors import AppError
from backend.shared.room_codes import UNAVAILABLE_MESSAGE, normalize_room_code

GAME_ID = "prompt-royale"
ACTIVE = {"prompting", "generating", "screening", "voting"}


def uid() -> str:
    return secrets.token_urlsafe(18)


@dataclass
class Player:
    id: str
    name: str
    seen: float


@dataclass
class Entry:
    id: str
    player: str
    prompt: str
    index: int
    status: str = "queued"
    attempts: int = 0
    retry_used: bool = False
    path: Path | None = None
    exclusion: str | None = None


@dataclass
class Round:
    id: str
    roster: tuple[str, ...]
    topic: str
    topic_mode: str
    seed: int
    phase: str
    deadline: float
    started: float
    submissions: dict[str, str] = field(default_factory=dict)
    entries: dict[str, Entry] = field(default_factory=dict)
    arena: list[str] = field(default_factory=list)
    ballot: tuple[str, ...] = ()
    votes: dict[str, str | None] = field(default_factory=dict)
    scores: dict[str, int] = field(default_factory=dict)
    winners: list[str] = field(default_factory=list)
    reason: str | None = None
    scored: bool = False


@dataclass
class Room:
    id: str
    code: str
    host: str
    mode: str
    seen: float
    players: dict[str, Player]
    sessions: dict[str, str]
    player_count: int = 3
    version: int = 1
    revision: int = 1
    closing: bool = False
    topic_mode: str = "bundled"
    topic: str | None = None
    suggestion_id: str | None = None
    confirmed_id: str | None = None
    topic_pending: bool = False
    topic_error: str | None = None
    round: Round | None = None
    receipts: dict[str, str] = field(default_factory=dict)


class Engine:
    def __init__(
        self,
        context: GameContext,
        settings: RoyaleSettings | None = None,
        video=None,
        topics=None,
        validator=None,
        clock=time.monotonic,
    ):
        self.context = context
        self.settings = settings or RoyaleSettings()
        self.clock = clock
        self.boot_id = uid()
        self.room: Room | None = None
        self.lock = asyncio.Lock()
        self.close_lock = asyncio.Lock()
        self.start_lock = asyncio.Lock()
        self.slots = asyncio.Semaphore(2)
        self.next_start = 0.0
        self.start_interval = 6.0
        self.starts = 0
        self.blocked = False
        self.tasks: set[asyncio.Task] = set()
        self.generation_tasks: set[asyncio.Task] = set()
        self.housekeeper: asyncio.Task | None = None
        self.root = context.settings.media_dir(GAME_ID)
        self.validator = validator or PromptValidator(self.settings.prompt_royale_tokenizer)
        self.journal = self.root.parent / "unresolved-provider.json"
        self.fixture_video = video if video is not None and not video.live else FixtureVideo()
        self.live_video = (
            video if video is not None and video.live else HeliosVideo(self.settings, self.journal)
        )
        self.video = (
            self.live_video if context.settings.generation_mode == "live" else self.fixture_video
        )
        self.topics = topics or Topics(self.settings)
        self.topic_task: asyncio.Task | None = None
        self.admission: dict[str, list[float]] = {}

    async def startup(self):
        self.root.mkdir(parents=True, exist_ok=True)
        if self.journal.exists():
            self.blocked = True
            await self.context.parties.set_blocker(
                GAME_ID, "A previous provider session needs operator verification."
            )
        # Only this game's disposable media, never another game's files or tokenizer.
        for path in self.root.iterdir():
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            else:
                path.unlink()
        self.housekeeper = asyncio.create_task(self._housekeeping())

    async def shutdown(self):
        if self.housekeeper:
            self.housekeeper.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.housekeeper
        await self._cancel_work()
        await self.video.close()
        if self.room and self.room.round:
            shutil.rmtree(self.root / self.room.round.id, ignore_errors=True)

    def _spawn(self, coroutine, generation=False):
        task = asyncio.create_task(coroutine)
        self.tasks.add(task)
        if generation:
            self.generation_tasks.add(task)

        def done(finished):
            self.tasks.discard(finished)
            self.generation_tasks.discard(finished)
            if not finished.cancelled():
                finished.exception()

        task.add_done_callback(done)
        return task

    def _changed(self, phase=False):
        self.room.revision += 1
        if phase:
            self.room.version += 1

    def _player(self, token: str | None, host=False, touch=True) -> Player:
        room = self.room
        if not room or token not in room.sessions:
            raise AppError(401, "session_expired", "Demo restarted or party ended — please rejoin.")
        player = room.players[room.sessions[token]]
        if host and player.id != room.host:
            raise AppError(403, "host_only", "Only the host can do that.")
        if touch:
            player.seen = self.clock()
            room.seen = self.clock()
        return player

    def summary(self, token: str | None):
        if not self.room or token not in self.room.sessions:
            return None
        return "host" if self.room.sessions[token] == self.room.host else "player"

    def _limit(self, ip: str):
        now = self.clock()
        self.admission = {
            k: [t for t in v if now - t < 60]
            for k, v in self.admission.items()
            if any(now - t < 60 for t in v)
        }
        attempts = self.admission.setdefault(ip, [])
        if len(attempts) >= 20:
            raise AppError(429, "too_many_attempts", "Wait a minute before trying again.")
        attempts.append(now)

    def _name(self, value):
        name = normalized(value, 24, "name")
        existing = {p.name for p in self.room.players.values()} if self.room else set()
        result = name
        index = 2
        while result in existing:
            suffix = f" ({index})"
            result = name[: 24 - len(suffix)] + suffix
            index += 1
        return result

    @staticmethod
    def _player_count(value):
        if type(value) is not int or not 1 <= value <= 4:
            raise AppError(422, "player_count", "Choose 1–4 players, including the host.")
        return value

    async def create(self, token, name, passcode, ip, player_count=3):
        async with self.lock:
            self._limit(ip)
            if self.summary(token) == "host":
                self._advance()
                player = self._player(token)
                return token, self.snapshot(player)
            configured = self.context.settings.host_passcode
            if not configured.strip() or configured.strip().lower() in {
                "change-me",
                "changeme",
                "your-passcode",
            }:
                raise AppError(503, "host_not_configured", "Configure the host access code first.")
            try:
                matches = secrets.compare_digest(passcode.encode(), configured.encode())
            except UnicodeEncodeError:
                matches = False
            if not matches:
                raise AppError(403, "passcode", "Incorrect host access code.", "passcode")
            name = normalized(name, 24, "name")
            player_count = self._player_count(player_count)
        async with self.context.parties.reserve(GAME_ID) as reservation:
            async with self.lock:
                now = self.clock()
                player = Player(uid(), name, now)
                token = uid()
                mode = self.context.settings.generation_mode
                if mode not in {"live", "fixture"}:
                    raise AppError(
                        503, "configuration", "Choose fixture or live mode in operator setup."
                    )
                if mode == "live" and not self.live_ready():
                    raise AppError(
                        503,
                        "live_not_ready",
                        self.live_unavailable_reason(),
                    )
                self.video = self.live_video if mode == "live" else self.fixture_video
                room = Room(
                    uid(),
                    reservation.code,
                    player.id,
                    mode,
                    now,
                    {player.id: player},
                    {token: player.id},
                    player_count=player_count,
                )
                self.room = room
            try:
                await reservation.activate()
            except BaseException:
                async with self.lock:
                    if self.room is room:
                        self.room = None
                raise
        return token, self.snapshot(player)

    def live_ready(self):
        return self.live_unavailable_reason() is None

    def live_unavailable_reason(self):
        s = self.settings
        if self.blocked or self.live_video.uncertain:
            return "Provider cleanup must finish before real generation is available."
        if not s.prompt_royale_live_enabled:
            return "Real generation is disabled in this server's Prompt Royale settings."
        if not s.prompt_royale_live_slot or s.prompt_royale_rehearsed_capacity < 1:
            return "Real generation needs a configured live slot and rehearsed player capacity."
        if not s.reactor_api_key:
            return "Real generation needs a Reactor API key on the server."
        if not self.live_video.live:
            return "The live video provider is unavailable."
        if self.validator.tokenizer is None:
            return "Install the verified Helios tokenizer before using real generation."
        return None

    async def join(self, token, name, code, ip):
        async with self.lock:
            self._limit(ip)
            self._advance()
            code = normalize_room_code(code)
            room = self.room
            if not room or room.code != code:
                raise AppError(
                    404,
                    "wrong_code",
                    UNAVAILABLE_MESSAGE,
                    "code",
                )
            if self.summary(token):
                return token, self.snapshot(self._player(token))
            if room.closing:
                raise AppError(409, "cleanup_pending", "The party is closing.")
            if room.round:
                raise AppError(
                    409, "round_active", "A round is in progress. Join when the lobby returns."
                )
            if len(room.players) >= room.player_count:
                raise AppError(
                    409,
                    "room_full",
                    "Room full. The host can increase the player count in the lobby, up to 4.",
                )
            player = Player(uid(), self._name(name), self.clock())
            token = uid()
            room.players[player.id] = player
            room.sessions[token] = player.id
            room.seen = self.clock()
            self._changed()
            return token, self.snapshot(player)

    async def state(self, token):
        async with self.lock:
            self._advance()
            return self.snapshot(self._player(token))

    def _lobby(self):
        if self.room.round:
            raise AppError(409, "wrong_phase", "Return to the lobby to change party settings.")

    def _round(self, data, phases):
        r = self.room.round
        if not r or r.id != data.get("round_id"):
            raise AppError(409, "round_changed", "The round changed. Refresh and try again.")
        if r.phase not in phases:
            raise AppError(409, "wrong_phase", "That action is no longer available.")
        return r

    async def mutate(self, token, action: str, data: dict):
        host = action not in {"submission", "vote"}
        async with self.lock:
            self._advance()
            player = self._player(token, host=host, touch=False)
            room = self.room
            if room.closing:
                raise AppError(409, "cleanup_pending", "The party is closing.")
            signature = json.dumps([action, data], sort_keys=True)
            command_id = data.get("command_id")
            if host:
                if not isinstance(command_id, str) or not 1 <= len(command_id) <= 80:
                    raise AppError(422, "command_id", "A command ID is required.")
                if command_id in room.receipts:
                    if room.receipts[command_id] != signature:
                        raise AppError(
                            409,
                            "command_changed",
                            "This command was already accepted with different details.",
                        )
                    return self._acknowledge(player)
                if data.get("expected_version") != room.version:
                    raise AppError(
                        409, "state_changed", "The screen changed. Check it and try again."
                    )
            if action == "generation-mode":
                self._lobby()
                mode = data.get("mode")
                if mode not in {"fixture", "live"}:
                    raise AppError(422, "generation_mode", "Choose fixture or real generation.")
                if self.blocked or self.video.uncertain:
                    raise AppError(
                        409, "cleanup_pending", "Provider cleanup must finish before switching."
                    )
                if mode == "live" and not self.live_ready():
                    raise AppError(409, "live_not_ready", self.live_unavailable_reason())
                self.video = self.live_video if mode == "live" else self.fixture_video
                room.mode = mode
                self._changed(True)
            elif action == "player-count":
                self._lobby()
                player_count = self._player_count(data.get("player_count"))
                if player_count < len(room.players):
                    raise AppError(
                        409,
                        "player_count",
                        "The player count cannot be below the number already joined.",
                    )
                room.player_count = player_count
                self._changed(True)
            elif action == "topic":
                self._lobby()
                mode = data["mode"]
                if mode not in {"bundled", "llm"}:
                    raise AppError(422, "topic_mode", "Choose a topic mode.")
                value = data.get("topic")
                if value is not None and (mode != "bundled" or value not in TOPICS):
                    raise AppError(422, "topic", "Choose a bundled topic.")
                self._clear_topic(mode)
                room.topic = value
                self._changed(True)
            elif action == "generate-topic":
                self._lobby()
                if room.topic_pending or (self.topic_task and not self.topic_task.done()):
                    raise AppError(
                        409, "topic_pending", "A topic suggestion is already on its way."
                    )
                self._clear_topic("llm")
                request_id = uid()
                room.suggestion_id = request_id
                room.topic_pending = True
                self._changed(True)
                self.topic_task = self._spawn(self._suggest(room, request_id))
            elif action == "confirm-topic":
                self._lobby()
                if (
                    room.topic_mode != "llm"
                    or room.topic_pending
                    or not room.topic
                    or data.get("suggestion_id") != room.suggestion_id
                ):
                    raise AppError(409, "stale_topic", "Confirm the current completed suggestion.")
                room.confirmed_id = room.suggestion_id
                self._changed(True)
            elif action == "start":
                self._lobby()
                if len(room.players) != room.player_count:
                    raise AppError(
                        409,
                        "player_count",
                        f"Waiting for {room.player_count} players, including the host.",
                    )
                if any(self.clock() - p.seen >= 30 for p in room.players.values()):
                    raise AppError(
                        409, "player_absent", "Everyone must be present. Ask them to open the game."
                    )
                if not room.topic or (
                    room.topic_mode == "llm"
                    and (room.topic_pending or room.confirmed_id != room.suggestion_id)
                ):
                    raise AppError(
                        409,
                        "topic_unconfirmed",
                        "Choose a topic or confirm the current LLM suggestion.",
                    )
                if self.validator.tokenizer is None:
                    raise AppError(
                        503, "tokenizer_missing", "Install the verified Helios tokenizer first."
                    )
                if room.mode == "live":
                    if (
                        not self.live_ready()
                        or len(room.players) > self.settings.prompt_royale_rehearsed_capacity
                    ):
                        raise AppError(
                            409, "live_capacity", "This live player count has not passed rehearsal."
                        )
                    if self.settings.prompt_royale_live_session_starts - self.starts < 2 * len(
                        room.players
                    ):
                        raise AppError(
                            409,
                            "allowance",
                            "Insufficient remaining video allowance for this round.",
                        )
                now = self.clock()
                room.round = Round(
                    uid(),
                    tuple(room.players),
                    room.topic,
                    room.topic_mode,
                    secrets.randbits(31),
                    "prompting",
                    now + 60,
                    now,
                )
                self._changed(True)
            elif action == "submission":
                r = self.room.round
                if r and data.get("round_id") == r.id and player.id in r.submissions:
                    if normalized(data["prompt"], 500, "prompt") == r.submissions[player.id]:
                        return self._acknowledge(player)
                    raise AppError(409, "submission_locked", "Your first accepted scene is locked.")
                r = self._round(data, {"prompting"})
                prompt, _ = self.validator.validate(r.topic, data["prompt"])
                r.submissions[player.id] = prompt
                self._changed()
                if len(r.submissions) == len(r.roster):
                    self._begin_generation(r)
            elif action == "exclude":
                r = self._round(data, {"screening"})
                entry = r.entries.get(data["entry_id"])
                if not entry or entry.id not in r.arena or entry.exclusion:
                    raise AppError(409, "ineligible_entry", "That clip is not eligible.")
                entry.exclusion = normalized(data["reason"], 120, "reason")
                self._changed(True)
            elif action == "open-voting":
                r = self._round(data, {"screening"})
                if data.get("watched") is not True:
                    raise AppError(
                        422, "watch_confirmation", "Confirm the group watched every remaining clip."
                    )
                r.ballot = tuple(eid for eid in r.arena if not r.entries[eid].exclusion)
                if len(r.ballot) < 2:
                    self._end(r, "Fewer than two clips remain. Unscored showcase.")
                else:
                    r.phase = "voting"
                    r.deadline = self.clock() + 10
                    self._changed(True)
            elif action == "vote":
                r = self.room.round
                choice = data.get("entry_id")
                if r and data.get("round_id") == r.id and player.id in r.votes:
                    if r.votes[player.id] == choice:
                        return self._acknowledge(player)
                    raise AppError(409, "ballot_locked", "Your ballot is already locked.")
                r = self._round(data, {"voting"})
                if choice is not None:
                    if choice not in r.ballot:
                        raise AppError(409, "ineligible_entry", "Choose an eligible clip.")
                    if r.entries[choice].player == player.id:
                        raise AppError(403, "self_vote", "Choose another player’s clip or abstain.")
                r.votes[player.id] = choice
                self._changed()
                if len(r.votes) == len(r.roster):
                    self._end(r)
            elif action == "abort":
                r = self._round(data, ACTIVE)
                self._end(r, "The host ended this round. No scores were awarded.")
            else:
                raise AppError(404, "unknown_action", "Unknown action.")
            player.seen = room.seen = self.clock()
            if host:
                room.receipts[command_id] = signature
                if len(room.receipts) > 256:
                    del room.receipts[next(iter(room.receipts))]
            return self._acknowledge(player)

    def _acknowledge(self, player):
        player.seen = self.room.seen = self.clock()
        return self.snapshot(player)

    def _clear_topic(self, mode="bundled"):
        room = self.room
        room.topic_mode = mode
        room.topic = room.suggestion_id = room.confirmed_id = room.topic_error = None
        room.topic_pending = False

    async def _suggest(self, room, request_id):
        try:
            topic = await self.topics.suggest()
            error = None
        except asyncio.CancelledError:
            return
        except Exception:
            topic = None
            error = "Topic suggestion failed. Try again or choose a bundled topic."
        async with self.lock:
            if (
                self.room is room
                and not room.closing
                and not room.round
                and room.topic_mode == "llm"
                and room.suggestion_id == request_id
            ):
                room.topic_pending = False
                room.topic = topic
                room.topic_error = error
                self._changed(True)

    def _begin_generation(self, r):
        r.phase = "generating"
        r.deadline = self.clock() + 180
        r.started = self.clock()
        entries = list(r.submissions.items())
        secrets.SystemRandom().shuffle(entries)
        r.entries = {
            e.id: e
            for i, (pid, prompt) in enumerate(entries)
            for e in [Entry(uid(), pid, prompt, i)]
        }
        self._changed(True)
        for entry in r.entries.values():
            self._spawn(self._generate(r, entry), generation=True)
        if not entries:
            self._screen(r)

    async def _entry_status(self, r, entry, status):
        async with self.lock:
            if self.room and self.room.round is r and r.phase == "generating":
                entry.status = status
                self._changed()

    def _can_generate(self, r):
        return (
            self.room and not self.room.closing and self.room.round is r and r.phase == "generating"
        )

    async def _generate(self, r, entry):
        folder = self.root / r.id
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"{entry.id}.mp4"
        source = None
        try:
            for recovery in range(2):
                try:
                    async with self.slots:
                        if not self._can_generate(r):
                            return
                        if self.video.live:
                            if source is None:
                                async with self.start_lock:
                                    await asyncio.sleep(max(0, self.next_start - self.clock()))
                                    async with self.lock:
                                        if not self._can_generate(r) or self.blocked:
                                            return
                                        if (
                                            r.deadline - self.clock() < 80
                                            or self.starts
                                            >= self.settings.prompt_royale_live_session_starts
                                        ):
                                            raise ProviderFailure("Insufficient time or allowance")
                                        self.starts += 1
                                        entry.attempts += 1
                                        self.next_start = self.clock() + self.start_interval
                            elif r.deadline - self.clock() < getattr(source, "runway", 20):
                                raise ProviderFailure("Insufficient preparation time")
                        async with asyncio.timeout(max(0.01, r.deadline - self.clock())):
                            await self.video.generate(
                                rendered(r.topic, entry.prompt),
                                r.seed,
                                target,
                                entry.index,
                                lambda s: self._entry_status(r, entry, s),
                                source,
                            )
                        async with self.lock:
                            self._advance()
                            if self._can_generate(r):
                                entry.path = target
                                entry.status = "ready"
                                self._changed()
                                return
                        return
                except ProviderFailure as error:
                    if error.uncertain or self.video.uncertain:
                        self.blocked = True
                        await self.context.parties.set_blocker(
                            GAME_ID, "Provider closure needs operator verification."
                        )
                    if (
                        recovery
                        or not error.transient
                        or error.uncertain
                        or self.blocked
                        or not self._can_generate(r)
                    ):
                        break
                    source = error.source
                    if (
                        self.video.live
                        and source is None
                        and self.starts >= self.settings.prompt_royale_live_session_starts
                    ):
                        break
                    required = getattr(source, "runway", 20) if source else 80
                    if r.deadline - self.clock() < required + error.retry_after:
                        break
                    entry.retry_used = True
                    await self._entry_status(r, entry, "retrying")
                    await asyncio.sleep(error.retry_after)
        except asyncio.CancelledError:
            raise
        except Exception:
            pass  # A failed entry cannot take down the other entries or reveal input.
        finally:
            target.with_suffix(".source.mp4").unlink(missing_ok=True)
            if entry.path is None:
                target.unlink(missing_ok=True)
            async with self.lock:
                if self._can_generate(r):
                    if entry.status != "ready":
                        entry.status = "unavailable"
                    self._changed()
                    if all(e.status in {"ready", "unavailable"} for e in r.entries.values()):
                        self._screen(r)

    def _screen(self, r):
        r.arena = [e.id for e in r.entries.values() if e.status == "ready" and e.path]
        secrets.SystemRandom().shuffle(r.arena)
        if not r.arena:
            self._end(r, "No clips were completed. This round is unscored.")
            return
        r.phase = "screening"
        r.deadline = self.clock() + 180
        self._changed(True)

    def _end(self, r, reason=None):
        if r.phase == "results":
            return
        if not r.arena:
            r.arena = [e.id for e in r.entries.values() if e.status == "ready" and e.path]
        r.scored = reason is None and len(r.ballot) >= 2
        counts = Counter(choice for choice in r.votes.values() if choice is not None)
        r.scores = {eid: counts[eid] if r.scored else 0 for eid in r.arena}
        maximum = max(r.scores.values(), default=0)
        r.winners = [eid for eid, count in r.scores.items() if count == maximum and maximum > 0]
        r.phase = "results"
        r.deadline = 0
        r.reason = reason or ("No votes were cast. No winner." if maximum == 0 else None)
        self._changed(True)
        for task in self.generation_tasks:
            if task is not asyncio.current_task():
                task.cancel()

    def _advance(self):
        room = self.room
        if not room or room.closing:
            return
        now = self.clock()
        if now - room.seen >= 7200:
            room.closing = True
            self._spawn(self.close(None, expiry=True))
            return
        r = room.round
        if not r or r.phase not in ACTIVE:
            return
        if now - room.players[room.host].seen >= 30:
            self._end(r, "The host was away for 30 seconds. This round is unscored.")
        elif now >= r.deadline:
            if r.phase == "prompting":
                self._begin_generation(r)
            elif r.phase == "generating":
                for task in self.generation_tasks:
                    if task is not asyncio.current_task():
                        task.cancel()
                for entry in r.entries.values():
                    if entry.status != "ready":
                        entry.status = "unavailable"
                self._screen(r)
            elif r.phase == "screening":
                self._end(r, "Arena screening was not completed.")
            elif r.phase == "voting":
                self._end(r)

    async def tick(self):
        async with self.lock:
            self._advance()

    async def _housekeeping(self):
        while True:
            await asyncio.sleep(1)
            await self.tick()

    async def _cancel_work(self):
        tasks = [t for t in self.tasks if t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    def _delete_round(self, round_id):
        folder = self.root / round_id
        try:
            if folder.exists():
                shutil.rmtree(folder)
        except OSError as error:
            raise AppError(
                409, "cleanup_pending", "Could not clear round media. Retry cleanup."
            ) from error

    async def again(self, token, data):
        async with self.close_lock:
            async with self.lock:
                self._advance()
                player = self._player(token, host=True)
                room = self.room
                if room.closing:
                    raise AppError(409, "cleanup_pending", "Finishing the previous round.")
                receipt = data.get("command_id")
                signature = json.dumps(["again", data], sort_keys=True)
                if receipt in room.receipts:
                    if room.receipts[receipt] != signature:
                        raise AppError(
                            409, "command_changed", "This command already has a receipt."
                        )
                    return self.snapshot(player)
                self._round(data, {"results"})
                if data.get("expected_version") != room.version:
                    raise AppError(409, "state_changed", "The screen changed. Try again.")
                room.closing = True
                r = room.round
            await self._cancel_work()
            closed = await self.video.close()
            async with self.lock:
                if not closed or (self.blocked and not self.video.live):
                    room.closing = False
                    raise AppError(
                        409, "cleanup_pending", "Provider closure needs operator verification."
                    )
            self.blocked = False
            await self.context.parties.set_blocker(GAME_ID, None)
            try:
                self._delete_round(r.id)
            except AppError:
                async with self.lock:
                    room.closing = False
                raise
            async with self.lock:
                room.round = None
                if receipt:
                    room.receipts[receipt] = signature
                room.closing = False
                self._clear_topic()
                self._changed(True)
                return self.snapshot(player)

    async def close(self, token, expiry=False):
        async with self.close_lock:
            async with self.lock:
                room = self.room
                if not room:
                    return True
                if not expiry:
                    self._player(token, host=True)
                room.closing = True
            await self.context.parties.begin_close(GAME_ID)
            await self._cancel_work()
            closed = await self.video.close()
            if not closed or (self.blocked and not self.video.live):
                await self.context.parties.set_blocker(
                    GAME_ID, "Provider closure needs operator verification."
                )
                return False
            self.blocked = False
            await self.context.parties.set_blocker(GAME_ID, None)
            if room.round:
                self._delete_round(room.round.id)
            async with self.lock:
                self.room = None
            await self.context.parties.finish_close(GAME_ID)
            return True

    async def media(self, token, opaque_id):
        async with self.lock:
            self._advance()
            self._player(token, touch=False)
            self.room.seen = self.clock()
            if self.room.closing:
                raise AppError(404, "media_unavailable", "This clip is being cleared.")
            r = self.room.round
            if (
                not r
                or r.phase not in {"screening", "voting", "results"}
                or opaque_id not in r.arena
            ):
                raise AppError(404, "media_unavailable", "This clip is not available.")
            entry = r.entries[opaque_id]
            if entry.exclusion or not entry.path:
                raise AppError(404, "media_unavailable", "This clip is not available.")
            return entry.path

    def snapshot(self, player: Player) -> dict[str, Any]:
        room = self.room
        r = room.round
        host = player.id == room.host
        result = {
            "boot_id": self.boot_id,
            "revision": room.revision,
            "version": room.version,
            "server_time": time.time(),
            "room_id": room.id,
            "code": room.code,
            "join_url": (
                f"{self.context.settings.public_origin}/games/{GAME_ID}/join?code={room.code}"
            ),
            "mode": room.mode,
            "topic_source": self.settings.prompt_royale_topic_mode,
            "phase": r.phase if r else "lobby",
            "closing": room.closing,
            "player_count": room.player_count,
            "players": [
                {
                    "id": p.id,
                    "name": p.name,
                    "host": p.id == room.host,
                    "present": self.clock() - p.seen < 30,
                }
                for p in room.players.values()
            ],
            "me": {"id": player.id, "name": player.name, "host": host},
            "round_id": r.id if r else None,
            "seconds_left": max(0, r.deadline - self.clock()) if r and r.deadline else 0,
            "topic": r.topic if r else None,
            "cleanup_pending": self.blocked,
        }
        if host:
            result["lobby"] = {
                "mode": room.topic_mode,
                "topic": room.topic,
                "suggestion_id": room.suggestion_id,
                "confirmed": bool(room.confirmed_id) and room.confirmed_id == room.suggestion_id,
                "pending": room.topic_pending,
                "error": room.topic_error,
                "topics": TOPICS,
                "live_unavailable_reason": self.live_unavailable_reason(),
                "live_capacity": self.settings.prompt_royale_rehearsed_capacity,
                "video_starts_remaining": self.settings.prompt_royale_live_session_starts
                - self.starts,
                "topic_calls_remaining": self.settings.prompt_royale_topic_calls
                - self.topics.calls,
            }
        if r:
            result["submitted"] = len(r.submissions)
            result["progress"] = dict(Counter(e.status for e in r.entries.values()))
            result["me"]["prompt"] = r.submissions.get(player.id)
            result["me"]["voted"] = player.id in r.votes
            result["me"]["vote"] = r.votes.get(player.id)
            if r.phase in {"screening", "voting", "results"}:
                tiles = []
                for position in range(4):
                    tile = {
                        "label": f"Clip {position + 1}",
                        "position": position,
                        "status": "empty",
                    }
                    if position < len(r.arena):
                        entry = r.entries[r.arena[position]]
                        tile.update(id=entry.id, status="excluded" if entry.exclusion else "ready")
                        if entry.exclusion:
                            tile["reason"] = entry.exclusion
                        else:
                            tile["url"] = f"/api/games/{GAME_ID}/media/{entry.id}"
                            if r.phase == "voting":
                                tile["own"] = entry.player == player.id
                            if r.phase == "results":
                                tile.update(
                                    author=room.players[entry.player].name,
                                    prompt=entry.prompt,
                                    votes=r.scores.get(entry.id, 0),
                                    winner=entry.id in r.winners,
                                )
                    tiles.append(tile)
                result["arena"] = tiles
            if r.phase == "results":
                result.update(scored=r.scored, reason=r.reason, winners=r.winners)
        return result
