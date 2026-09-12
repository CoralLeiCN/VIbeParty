import asyncio
import contextlib
import logging
import secrets
import shutil
import time
from collections.abc import Callable
from pathlib import Path

from backend.shared.contracts import GameContext
from backend.shared.errors import AppError
from backend.shared.room_codes import UNAVAILABLE_MESSAGE, normalize_room_code

from .domain import (
    DEFAULT_DISALLOWED,
    FIXTURE_TEXT,
    GAME_ID,
    Player,
    Room,
    Round,
    Slot,
    identifier,
    validate_text,
)
from .live import FastH3Provider, LiveSettings
from .providers import FixtureProvider, Provider

log = logging.getLogger(__name__)


class Game:
    def __init__(
        self,
        context: GameContext,
        *,
        provider_factory: Callable[[str], Provider] | None = None,
        clock: Callable[[], float] = time.time,
        input_seconds: float = 45,
        total_seconds: float = 120,
        step_seconds: float = 30,
        expiry_seconds: float = 1800,
        attempt_limit: int = 3,
    ):
        self.context = context
        self.clock = clock
        self.lock = asyncio.Lock()
        self.admission_lock = asyncio.Lock()
        self.lifecycle_lock = asyncio.Lock()
        self.room: Room | None = None
        self.task: asyncio.Task | None = None
        self.cleanup_task: asyncio.Task | None = None
        self.deadline_task: asyncio.Task | None = None
        self.expiry_task: asyncio.Task | None = None
        self.expiry_retry_at = 0.0
        self.provider: Provider | None = None
        self.provider_closing = False
        self.attempts = 0
        self.attempt_limit = attempt_limit
        self.input_seconds = input_seconds
        self.total_seconds = total_seconds
        self.step_seconds = step_seconds
        self.expiry_seconds = expiry_seconds
        self.media = context.settings.media_dir(GAME_ID)
        self.factory = provider_factory or self.default_provider
        self.live_settings = LiveSettings()
        self.live_reason = self.live_settings.unavailable_reason()
        self.disallowed = DEFAULT_DISALLOWED

    def default_provider(self, mode: str) -> Provider:
        if mode == "fixture":
            return FixtureProvider()
        if self.live_reason:
            raise AppError(503, "live_unavailable", self.live_reason)
        return FastH3Provider(
            self.live_settings.reactor_api_key.get_secret_value(),
            evidence_path=self.media.parent / "live-evidence" / f"{identifier()}.json",
        )

    async def startup(self) -> None:
        # Only this game's disposable directory. Fixture source assets live elsewhere.
        await asyncio.to_thread(self.clear_files)
        self.deadline_task = asyncio.create_task(self.deadlines())

    def clear_files(self) -> None:
        if self.media.is_symlink():
            raise RuntimeError("Private clip directory must not be a symlink")
        if self.media.exists():
            shutil.rmtree(self.media)
        self.media.mkdir(parents=True, mode=0o700)

    def authenticate(self, token: str | None, host: bool = False) -> Room:
        room = self.room
        if not room or not room.role(token):
            raise AppError(
                401,
                "session_expired" if token else "no_session",
                "This party has ended. Join again to play." if token else "Join the party to play.",
            )
        if host and room.role(token) != "host":
            raise AppError(403, "host_required", "Only the host can do that.")
        return room

    def round_for(self, token: str | None, round_id: str, host: bool = True) -> Room:
        room = self.authenticate(token, host)
        if room.round.id != round_id:
            raise AppError(409, "stale_round", "The round changed. Refresh your screen.")
        if room.closing or room.maintenance:
            raise AppError(409, "cleanup_pending", "Finishing the previous session. Please wait.")
        return room

    def snapshot(self, token: str) -> dict:
        room = self.authenticate(token)
        return room.snapshot(
            token,
            self.clock(),
            self.context.settings.public_origin,
            self.provider_closing,
            max(0, self.attempt_limit - self.attempts),
            self.live_reason,
        )

    def busy(self) -> bool:
        return self.provider_closing or bool(self.task and not self.task.done())

    async def host(self, passcode: str, token: str | None) -> tuple[str, dict]:
        configured = self.context.settings.host_passcode
        if not configured or configured.lower() in {"change-me", "changeme", "your-passcode"}:
            raise AppError(
                503, "host_not_configured", "Ask the presenter to configure the host passcode."
            )
        if not secrets.compare_digest(passcode.encode(), configured.encode()):
            raise AppError(403, "wrong_passcode", "That host passcode is incorrect.", "passcode")
        # Admission and game locks never nest with the shared coordinator lock.
        async with self.admission_lock:
            async with self.lock:
                if self.room:
                    if self.room.role(token) != "host":
                        raise AppError(
                            409,
                            "host_already_present",
                            "Reopen the host screen in its original browser.",
                        )
                    self.room.touch(self.clock())
                    return token, self.snapshot(token)
            async with self.context.parties.reserve(GAME_ID) as reservation:
                host_token = identifier()
                room = Room(
                    host=host_token, code=reservation.code, activity=self.clock(), maintenance=True
                )
                async with self.lock:
                    self.room = room
                try:
                    await reservation.activate()
                except BaseException:
                    async with self.lock:
                        self.room = None
                    raise
                async with self.lock:
                    room.maintenance = False
                    return host_token, self.snapshot(host_token)

    async def join(self, code: object, name: str, token: str | None) -> tuple[str, dict]:
        code = normalize_room_code(code)
        async with self.lock:
            room = self.room
            if not room or room.code != code or room.closing:
                raise AppError(
                    404,
                    "party_unavailable",
                    UNAVAILABLE_MESSAGE,
                    "code",
                )
            if room.role(token):
                room.touch(self.clock())
                return token, self.snapshot(token)
            if room.maintenance:
                raise AppError(409, "cleanup_pending", "Finishing the previous session.")
            if room.round.phase != "LOBBY":
                raise AppError(
                    409, "round_in_progress", "A round is in progress. Try again in the lobby."
                )
            if len(room.players) >= room.player_count:
                raise AppError(409, "party_full", "This party is full.")
            name = name.strip()
            if not 1 <= len(name) <= 24 or any(
                ord(char) < 32 or 0xD800 <= ord(char) <= 0xDFFF for char in name
            ):
                raise AppError(
                    422, "invalid_name", "Use a name between 1 and 24 characters.", "name"
                )
            player_token = identifier()
            room.players.append(Player(player_token, name))
            room.touch(self.clock())
            return player_token, self.snapshot(player_token)

    async def set_player_count(self, token: str, round_id: str, player_count: int) -> dict:
        async with self.lock:
            room = self.round_for(token, round_id)
            if room.round.phase != "LOBBY":
                raise AppError(409, "round_started", "Change the player count in the lobby.")
            if self.busy():
                raise AppError(409, "cleanup_pending", "Finishing the previous session.")
            if type(player_count) is not int or not 1 <= player_count <= 4:
                raise AppError(422, "invalid_player_count", "Choose between 1 and 4 players.")
            if player_count < len(room.players):
                raise AppError(
                    409,
                    "players_already_joined",
                    "Reset the roster before choosing fewer players than have already joined.",
                )
            room.player_count = player_count
            room.touch(self.clock())
            return self.snapshot(token)

    async def start(self, token: str, round_id: str, mode: str) -> dict:
        async with self.lock:
            room = self.round_for(token, round_id)
            r = room.round
            if r.phase != "LOBBY":
                raise AppError(409, "round_started", "This round has already started.")
            if len(room.players) != room.player_count:
                raise AppError(
                    409, "need_players", "Wait for the selected number of players to join."
                )
            if self.busy():
                raise AppError(409, "cleanup_pending", "Finishing the previous session.")
            if mode not in {"fixture", "live"}:
                raise AppError(422, "invalid_mode", "Choose fixture or live mode.")
            if mode == "live":
                if self.live_reason:
                    raise AppError(503, "live_unavailable", self.live_reason)
                if self.attempts >= self.attempt_limit:
                    raise AppError(
                        409,
                        "attempts_exhausted",
                        "The live session limit for this server run is reached.",
                    )
            r.mode = mode
            r.phase = "INPUT"
            r.slots = [Slot(i, room.players[i % len(room.players)].token) for i in range(4)]
            r.input_deadline = self.clock() + self.input_seconds
            room.touch(self.clock())
            return self.snapshot(token)

    def expire_input(self, room: Room) -> None:
        r = room.round
        if r.phase == "INPUT" and self.clock() >= r.input_deadline:
            r.phase = "RESULTS"
            r.result = "incomplete"
            r.message = "Time is up. We did not collect all four contributions. Try another round."
            room.revision += 1

    async def contribute(self, token: str, round_id: str, index: int, raw: str) -> dict:
        text = validate_text(raw, self.disallowed)
        async with self.lock:
            room = self.round_for(token, round_id, host=False)
            r = room.round
            if index not in range(len(r.slots)) or r.slots[index].owner != token:
                raise AppError(
                    403, "slot_not_yours", "You can only submit your assigned contributions."
                )
            slot = r.slots[index]
            if slot.text is not None:
                if slot.text != text:
                    raise AppError(
                        409, "contribution_locked", "Your accepted contribution is locked."
                    )
                return self.snapshot(token)
            self.expire_input(room)
            if r.phase != "INPUT":
                raise AppError(
                    409, "collection_closed", "This round is no longer collecting contributions."
                )
            if r.mode == "fixture" and text != FIXTURE_TEXT[index]:
                raise AppError(
                    422,
                    "fixture_text_required",
                    "Use the shown example in this fixture rehearsal.",
                    "text",
                )
            slot.text = text
            room.touch(self.clock())
            if all(slot.text is not None for slot in r.slots):
                r.phase = "GENERATING"
                r.generation_deadline = self.clock() + self.total_seconds
                # Retain under the lock before another submission can observe this transition.
                self.task = asyncio.create_task(self.generate(room, r))
            return self.snapshot(token)

    async def generate(self, room: Room, r: Round) -> None:
        provider = None
        cancelled = False
        failure = None
        try:
            async with asyncio.timeout(self.total_seconds):
                async with self.lock:
                    if self.room is not room or room.round is not r or r.phase != "GENERATING":
                        return
                    if r.mode == "live":
                        if self.provider_closing or self.attempts >= self.attempt_limit:
                            raise RuntimeError("live_admission_blocked")
                        self.attempts += 1
                    self.provider_closing = True
                    provider = self.factory(r.mode)
                    self.provider = provider
                await provider.open()
                texts = [slot.text for slot in r.slots]
                for index in range(4):
                    started = time.monotonic()
                    destination = self.media / r.id / f"{index}.mp4"
                    async with asyncio.timeout(self.step_seconds):
                        clip = await provider.segment(texts, index, destination)
                    async with self.lock:
                        current = self.room is room and room.round is r and r.phase == "GENERATING"
                        if current:
                            r.clips.append(clip)
                            room.revision += 1
                    if not current:
                        await asyncio.to_thread(destination.unlink, missing_ok=True)
                        break
                    log.info(
                        "word_by_word round=%s step=%s seconds=%.3f",
                        r.id,
                        index,
                        time.monotonic() - started,
                    )
        except asyncio.CancelledError:
            cancelled = True
        except Exception as error:
            failure = "timeout" if isinstance(error, TimeoutError) else "generation_failed"
            log.warning("word_by_word round=%s failure=%s attempt=%s", r.id, failure, self.attempts)
        finally:
            async with self.lock:
                if self.room is room and room.round is r and r.phase == "GENERATING":
                    r.result = (
                        "complete" if len(r.clips) == 4 else "partial" if r.clips else "failed"
                    )
                    r.message = (
                        "Your story is ready."
                        if r.result == "complete"
                        else "Partial story. Generation stopped; the saved beginning is ready."
                        if r.clips
                        else "Generation timed out. Try another round after cleanup."
                        if failure == "timeout"
                        else "No usable video was saved. Try another round after cleanup."
                    )
                    r.phase = "REVEAL" if r.clips and not cancelled else "RESULTS"
                    room.revision += 1
                if provider is not None:
                    self.cleanup_task = asyncio.create_task(self.cleanup(provider))
                else:
                    self.provider_closing = False

    async def cleanup(self, provider: Provider) -> None:
        confirmed = False
        try:
            confirmed = await asyncio.wait_for(provider.close(), 20)
        except (Exception, asyncio.CancelledError):
            log.warning("word_by_word provider_cleanup_unresolved")
        async with self.lock:
            if self.provider is provider and confirmed:
                self.provider_closing = False
                self.provider = None
            if self.room:
                self.room.revision += 1

    async def retry_cleanup(self, token: str, round_id: str) -> dict:
        async with self.lock:
            self.round_for(token, round_id)
            if self.task and not self.task.done():
                raise AppError(409, "generation_active", "End the round before retrying cleanup.")
            if self.provider and (not self.cleanup_task or self.cleanup_task.done()):
                self.cleanup_task = asyncio.create_task(self.cleanup(self.provider))
            return self.snapshot(token)

    async def reveal(self, token: str, round_id: str, expected: int) -> dict:
        async with self.lock:
            room = self.round_for(token, round_id)
            r = room.round
            if r.phase != "REVEAL" or r.disclosed != expected:
                raise AppError(
                    409, "reveal_changed", "The reveal moved on. Your screen will catch up."
                )
            if r.disclosed + 1 < len(r.clips):
                r.disclosed += 1
            else:
                r.phase = "RESULTS"
            room.touch(self.clock())
            return self.snapshot(token)

    async def end(self, token: str, round_id: str) -> dict:
        async with self.lock:
            room = self.round_for(token, round_id)
            if room.round.phase == "LOBBY":
                raise AppError(409, "round_not_started", "Start the round first.")
            r = room.round
            if r.phase != "RESULTS":
                r.phase = "RESULTS"
                r.result = "ended"
                r.message = "Round ended. Only the additions already revealed are shown."
                room.touch(self.clock())
                if self.task and not self.task.done():
                    self.task.cancel()
            return self.snapshot(token)

    async def new_round(self, token: str, round_id: str, reset: bool = False) -> dict:
        async with self.lifecycle_lock:
            async with self.lock:
                room = self.round_for(token, round_id)
                if room.round.phase not in ({"LOBBY", "RESULTS"} if reset else {"RESULTS"}):
                    raise AppError(409, "finish_round", "End this round first.")
                if self.busy():
                    raise AppError(409, "cleanup_pending", "Finishing the previous session.")
                if room.round.mode == "live" and self.attempts >= self.attempt_limit and not reset:
                    raise AppError(
                        409,
                        "attempts_exhausted",
                        "The live session limit for this server run is reached.",
                    )
                room.maintenance = True
            try:
                await asyncio.to_thread(self.clear_files)
                next_code = await self.context.parties.rotate_code(GAME_ID) if reset else room.code
                async with self.lock:
                    room.code = next_code
                    if reset:
                        room.players.clear()
                    room.round = Round()
                    room.touch(self.clock())
            finally:
                async with self.lock:
                    room.maintenance = False
            async with self.lock:
                return self.snapshot(token)

    async def clip_path(self, token: str | None, round_id: str, index: int) -> Path:
        async with self.lock:
            room = self.authenticate(token, host=True)
            r = room.round
            if (
                room.maintenance
                or r.id != round_id
                or index < 0
                or index > r.disclosed
                or index >= len(r.clips)
            ):
                raise AppError(404, "clip_unavailable", "That clip is not available.")
            path = r.clips[index].path
        if not await asyncio.to_thread(path.is_file):
            raise AppError(404, "clip_unavailable", "This replay is no longer available.")
        return path

    async def close(self, token: str | None = None, *, expired: bool = False) -> bool:
        async with self.lifecycle_lock:
            async with self.lock:
                if self.room is None:
                    return True
                room = self.room if expired else self.authenticate(token, host=True)
                room.closing = True
                room.round.phase = "RESULTS"
                room.round.message = "Closing this party. Everyone will need to rejoin."
                room.revision += 1
                task = self.task
                if task and not task.done():
                    task.cancel()
            await self.context.parties.begin_close(GAME_ID)
            if task:
                with contextlib.suppress(asyncio.CancelledError, TimeoutError):
                    await asyncio.wait_for(asyncio.shield(task), 2)
            if self.provider and (not self.cleanup_task or self.cleanup_task.done()):
                self.cleanup_task = asyncio.create_task(self.cleanup(self.provider))
            if self.cleanup_task:
                with contextlib.suppress(asyncio.CancelledError, TimeoutError):
                    await asyncio.wait_for(asyncio.shield(self.cleanup_task), 2)
            async with self.lock:
                if self.busy():
                    return False
            await asyncio.to_thread(self.clear_files)
            async with self.lock:
                self.room = None
            await self.context.parties.finish_close(GAME_ID)
            return True

    async def tick(self) -> None:
        async with self.lock:
            room = self.room
            if not room:
                return
            self.expire_input(room)
            expired = self.clock() - room.activity >= self.expiry_seconds
            if (
                expired
                and self.clock() >= self.expiry_retry_at
                and (not self.expiry_task or self.expiry_task.done())
            ):
                self.expiry_retry_at = self.clock() + 5
                self.expiry_task = asyncio.create_task(self.close(expired=True))

    async def deadlines(self) -> None:
        while True:
            await asyncio.sleep(0.25)
            await self.tick()

    async def shutdown(self) -> None:
        if self.deadline_task:
            self.deadline_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.deadline_task
        if self.expiry_task:
            with contextlib.suppress(asyncio.CancelledError):
                await self.expiry_task
        if self.room:
            await self.close(expired=True)
        if self.cleanup_task and not self.cleanup_task.done():
            with contextlib.suppress(asyncio.CancelledError):
                await self.cleanup_task
