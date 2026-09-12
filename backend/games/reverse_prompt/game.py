import asyncio
import secrets
import shutil
import time
from dataclasses import dataclass, field
from uuid import uuid4

from backend.shared.contracts import GameContext
from backend.shared.errors import AppError
from backend.shared.room_codes import UNAVAILABLE_MESSAGE, normalize_room_code

from .config import GameSettings
from .quota import GuardError, Quota
from .reactor_video import FastH3Provider
from .rehearsal import GUESSES, PROMPTS, SAMPLE_SCORES, RehearsalProvider
from .scoring import LocalScorer, normalize

GAME = "reverse-prompt"


def identifier():
    return str(uuid4())


@dataclass
class Player:
    role: str
    name: str
    token: str = field(default_factory=lambda: secrets.token_urlsafe(32))


@dataclass
class Round:
    id: str = field(default_factory=identifier)
    phase: str = "lobby"
    step: int = 0
    prompts: list = field(default_factory=lambda: [None, None, None])
    media: list = field(default_factory=list)
    guesses: dict = field(default_factory=dict)
    receipts: dict = field(default_factory=dict)
    scores: list | None = None
    unscored: bool = False
    error: str | None = None
    generation_started: float | None = None


@dataclass
class Room:
    mode: str
    players: list
    code: str
    id: str = field(default_factory=identifier)
    round: Round = field(default_factory=Round)
    revision: int = 1
    closing: bool = False


class Game:
    def __init__(self, context: GameContext, config=None, scorer=None, provider=None):
        self.context = context
        self.config = config or GameSettings()
        self.lock = asyncio.Lock()
        self.room: Room | None = None
        self.scorer = scorer or LocalScorer()
        self.quota = Quota(context.settings.reverse_prompt_quota_file)
        self.guard = None
        self.guard_error = None
        self.media_root = context.settings.media_dir(GAME)
        self.live_provider = provider or FastH3Provider(
            self.config.reactor_api_key.get_secret_value(), self.quota
        )
        self.work: asyncio.Task | None = None
        self.inference: asyncio.Task | None = None
        self.cleanup: asyncio.Task | None = None
        self.retired: Round | None = None
        self.generation_timeout = 90
        self.scoring_timeout = 15

    async def startup(self):
        # Only our disposable media tree is removed. Never traverse model/quota paths.
        for persistent in (self.quota.path, self.context.settings.embedding_model_path):
            if persistent.is_relative_to(self.media_root) or self.media_root.is_relative_to(
                persistent
            ):
                raise RuntimeError("Persistent files must be separate from disposable clips")
        await asyncio.to_thread(shutil.rmtree, self.media_root, True)
        self.media_root.mkdir(parents=True, exist_ok=True)
        await self.refresh_guard()
        if not self.scorer.ready:
            try:
                await asyncio.to_thread(
                    self.scorer.load, self.context.settings.embedding_model_path
                )
            except Exception:
                self.scorer.ready = False

    async def refresh_guard(self):
        try:
            self.guard = await asyncio.to_thread(self.quota.read)
            self.guard_error = None
        except GuardError as error:
            self.guard = None
            self.guard_error = str(error)
        unresolved = (self.guard and self.guard["unresolved"]) or (
            self.guard is None and self.quota.path.exists()
        )
        await self.context.parties.set_blocker(
            GAME,
            "Previous video session needs operator closure verification." if unresolved else None,
        )
        return bool(unresolved)

    def member(self, token: str | None) -> Player:
        if self.room:
            for player in self.room.players:
                if token and secrets.compare_digest(token.encode(), player.token.encode()):
                    return player
        raise AppError(401, "session_expired", "This party has ended. Join again with your host.")

    def host(self, token):
        player = self.member(token)
        if player.role != "A":
            raise AppError(403, "host_only", "Only the host can do that.")
        return player

    def current(self, round_id, allow_cleanup=False):
        room = self.room
        if not room or room.round.id != round_id:
            raise AppError(409, "stale_round", "The round changed. Refresh before trying again.")
        if (room.closing or room.round.phase == "cleanup") and not allow_cleanup:
            raise AppError(409, "cleanup_pending", "Finishing the previous round. Please wait.")
        return room.round

    def name(self, value):
        value = normalize(value)
        if not 1 <= len(value) <= 24:
            raise AppError(422, "invalid_name", "Use a name with 1–24 characters.", "name")
        names = {p.name.casefold() for p in self.room.players} if self.room else set()
        candidate, suffix = value, 2
        while candidate.casefold() in names:
            candidate = f"{value} ({suffix})"
            suffix += 1
        return candidate

    def capacity_reason(self, mode):
        if not self.scorer.ready:
            return "The local scoring model is unavailable. Ask the host to check setup."
        if self.inference and not self.inference.done():
            return "The previous local comparison is still finishing."
        if self.guard and self.guard["unresolved"]:
            return "Previous video session needs operator closure verification."
        if mode == "live":
            if not self.config.reverse_prompt_live_enabled:
                return "Live generation needs an exclusive trial slot from the integration session."
            if not self.config.reactor_api_key.get_secret_value():
                return "Reactor credentials are unavailable."
            if not self.guard:
                return self.guard_error
            if self.guard["remaining"] < 3:
                return "Fewer than three live attempts remain in this campaign."
        return None

    async def create(self, token, organizer_code, name, mode):
        async with self.lock:
            try:
                existing = self.member(token)
            except AppError:
                existing = None
            if existing:
                return existing
        expected = (
            self.config.organizer_code.get_secret_value()
            if self.config.organizer_code is not None
            else self.context.settings.host_passcode
        )
        if not expected.strip() or expected.strip().lower() in {
            "change-me",
            "changeme",
            "your-passcode",
        }:
            raise AppError(
                503, "host_not_configured", "Ask the presenter to configure the organizer code."
            )
        if not secrets.compare_digest(organizer_code.encode(), expected.encode()):
            raise AppError(
                403, "wrong_organizer_code", "Check the organizer code.", "organizer_code"
            )
        name = self.name(name)
        if mode == "live" and not self.config.reverse_prompt_live_enabled:
            raise AppError(
                409, "live_disabled", "Live trials have not been enabled by the operator."
            )
        async with self.context.parties.reserve(GAME) as reservation:
            async with self.lock:
                player = Player("A", name)
                created = Room(mode, [player], code=reservation.code)
                self.room = created
            try:
                await reservation.activate()
            except BaseException:
                async with self.lock:
                    if self.room is created:
                        self.room = None
                raise
        return player

    async def join(self, token, code, name):
        code = normalize_room_code(code)
        async with self.lock:
            if not self.room or self.room.closing or code != self.room.code:
                raise AppError(404, "party_unavailable", UNAVAILABLE_MESSAGE, "code")
            try:
                return self.member(token)
            except AppError:
                pass
            if self.room.round.phase != "lobby":
                raise AppError(
                    409, "round_in_progress", "A round is in progress. Wait for the lobby."
                )
            if len(self.room.players) == 3:
                raise AppError(409, "party_full", "This party is full. Exactly three people play.")
            player = Player("ABC"[len(self.room.players)], self.name(name))
            self.room.players.append(player)
            self.room.revision += 1
            return player

    async def start(self, token, round_id):
        await self.refresh_guard()
        async with self.lock:
            self.host(token)
            round = self.current(round_id)
            if round.phase != "lobby" or len(self.room.players) != 3:
                raise AppError(
                    409, "cannot_start", "Start requires exactly three people in the lobby."
                )
            reason = self.capacity_reason(self.room.mode)
            if reason:
                raise AppError(409, "not_ready", reason)
            self.room.round = Round(phase="author_input")
            self.room.revision += 1
            return {"round_id": self.room.round.id}

    async def submit(self, token, body):
        async with self.lock:
            player = self.member(token)
            round = self.current(body.round_id)
            text = normalize(body.text)
            key = (player.role, str(body.submission_id))
            signature = (body.phase, body.step, text)
            if key in round.receipts:
                previous, receipt = round.receipts[key]
                if previous != signature:
                    raise AppError(
                        409, "submission_conflict", "An accepted submission cannot change."
                    )
                return receipt
            if body.phase != round.phase or body.step != round.step:
                raise AppError(409, "wrong_step", "Your turn changed. Refresh before submitting.")
            if round.phase in {"author_input", "relay_input"}:
                if player.role != "ABC"[round.step] or round.prompts[round.step] is not None:
                    raise AppError(
                        403, "not_your_turn", "Only the current player can describe this scene."
                    )
                scripted = PROMPTS[round.step]
            elif round.phase == "guessing":
                if player.role == "A":
                    raise AppError(403, "author_unscored", "The author does not submit a guess.")
                if player.role in round.guesses:
                    raise AppError(409, "already_accepted", "Your guess has already been accepted.")
                scripted = GUESSES[player.role]
            else:
                raise AppError(409, "wrong_phase", "There is no input to submit right now.")
            try:
                text = self.scorer.validate(text)
            except ValueError as error:
                raise AppError(422, "invalid_text", str(error), "text") from None
            if self.room.mode == "rehearsal" and text != scripted:
                raise AppError(
                    422,
                    "scripted_rehearsal",
                    "Use the supplied scene in this scripted rehearsal.",
                    "text",
                )
            receipt = {
                "status": "accepted",
                "submission_id": str(body.submission_id),
                "round_id": round.id,
            }
            round.receipts[key] = (signature, receipt)
            if round.phase == "guessing":
                round.guesses[player.role] = text
                if len(round.guesses) == 2:
                    round.phase = "scoring"
                    self.work = asyncio.create_task(self.score(round, self.room.mode))
            else:
                round.prompts[round.step] = text
                round.phase = "generating"
                round.generation_started = time.monotonic()
                self.work = asyncio.create_task(self.generate(round, self.room.mode))
            self.room.revision += 1
            return receipt

    async def generate(self, round, mode):
        provider = RehearsalProvider() if mode == "rehearsal" else self.live_provider
        step = round.step
        worker = asyncio.create_task(
            provider.generate(round.prompts[step], self.media_root / round.id / str(step), step)
        )
        try:
            done, _ = await asyncio.wait({worker}, timeout=self.generation_timeout)
            if not done:
                async with self.lock:
                    if self.room and self.room.round is round:
                        round.phase = "error"
                        round.unscored = True
                        round.error = "Video generation timed out. The round is unscored."
                        self.room.revision += 1
                worker.cancel()
                await asyncio.gather(worker, return_exceptions=True)
                return
            path = worker.result()
            async with self.lock:
                if self.room and self.room.round is round and round.phase == "generating":
                    round.media.append(
                        {"id": secrets.token_urlsafe(24), "step": step, "path": path}
                    )
                    if step == 2:
                        round.phase = "guessing"
                    else:
                        round.step += 1
                        round.phase = "relay_input"
                    self.room.revision += 1
        except asyncio.CancelledError:
            worker.cancel()
            await asyncio.gather(worker, return_exceptions=True)
            raise
        except Exception:
            async with self.lock:
                if self.room and self.room.round is round:
                    round.phase = "error"
                    round.unscored = True
                    round.error = (
                        "This video could not be made. The round is unscored. "
                        "The host can reset after cleanup."
                    )
                    self.room.revision += 1
        finally:
            await self.refresh_guard()

    async def score(self, round, mode):
        scores = None
        try:
            if mode == "rehearsal":
                await asyncio.sleep(0.3)
                scores = SAMPLE_SCORES.copy()
            else:
                self.inference = asyncio.create_task(
                    asyncio.to_thread(
                        self.scorer.score,
                        round.prompts[0],
                        [round.guesses["B"], round.guesses["C"]],
                    )
                )
                # Timeout/cancel never abandons the worker or permits overlapping inference.
                self.inference.add_done_callback(
                    lambda task: task.exception() if not task.cancelled() else None
                )
                scores = await asyncio.wait_for(
                    asyncio.shield(self.inference), self.scoring_timeout
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        async with self.lock:
            if self.room and self.room.round is round and round.phase == "scoring":
                round.scores = scores
                round.unscored = scores is None
                round.phase = "reveal"
                self.room.revision += 1

    def allowed_media(self, player, round):
        if round.phase == "reveal":
            return round.media
        if round.phase in {"guessing", "scoring"}:
            return [m for m in round.media if m["step"] == 2]
        if round.phase == "relay_input" and player.role == "ABC"[round.step]:
            return [m for m in round.media if m["step"] == round.step - 1]
        return []

    async def snapshot(self, token):
        await self.refresh_guard()
        if self.retired and (not self.cleanup or self.cleanup.done()):
            self.cleanup = asyncio.create_task(self.finish_cleanup())
        async with self.lock:
            player = self.member(token)
            room, round = self.room, self.room.round
            reason = self.capacity_reason(room.mode)
            media = self.allowed_media(player, round)

            def reference(m):
                return {
                    "id": m["id"],
                    "step": m["step"],
                    "url": f"/api/games/{GAME}/media/{m['id']}",
                }

            own = {
                "prompt": round.prompts["ABC".index(player.role)],
                "guess": round.guesses.get(player.role),
            }
            result = {
                "room_id": room.id,
                "round_id": round.id,
                "revision": room.revision,
                "code": room.code,
                "mode": room.mode,
                "phase": round.phase,
                "step": round.step,
                "role": player.role,
                "players": [{"role": p.role, "name": p.name} for p in room.players],
                "own": own,
                "media": [reference(m) for m in media],
                "guess_count": len(round.guesses),
                "token_limit": self.scorer.token_limit,
                "can_start": player.role == "A"
                and round.phase == "lobby"
                and len(room.players) == 3
                and not reason
                and not room.closing,
                "start_blocked": reason,
                "closing": room.closing,
                "error": round.error,
                "unscored": round.unscored,
                "join_url": (
                    f"{self.context.settings.public_origin}/games/{GAME}/join?code={room.code}"
                ),
                "generation_elapsed": int(time.monotonic() - round.generation_started)
                if round.phase == "generating"
                else None,
                "remaining_attempts": self.guard["remaining"] if self.guard else None,
                "cleanup_pending": bool(self.guard and self.guard["unresolved"]),
            }
            if room.mode == "rehearsal":
                if (
                    round.phase in {"author_input", "relay_input"}
                    and player.role == "ABC"[round.step]
                ):
                    result["scripted_text"] = PROMPTS[round.step]
                elif round.phase == "guessing" and player.role != "A":
                    result["scripted_text"] = GUESSES[player.role]
            if round.phase == "reveal":
                result["chain"] = [
                    {
                        "prompt": round.prompts[i],
                        "player": room.players[i].name,
                        "role": "ABC"[i],
                        "media": reference(round.media[i]),
                    }
                    for i in range(3)
                ]
                result["results"] = [
                    {
                        "role": role,
                        "player": room.players[i + 1].name,
                        "guess": round.guesses[role],
                        "points": round.scores[i] if round.scores is not None else None,
                        "winner": round.scores is not None and round.scores[i] == max(round.scores),
                    }
                    for i, role in enumerate("BC")
                ]
            return result

    async def reset(self, token, round_id, close=False):
        async with self.lock:
            self.host(token)
            if self.room.closing and not close:
                raise AppError(409, "closing", "The party is closing.")
            round = self.current(round_id, allow_cleanup=True)
            if round.phase != "cleanup":
                self.retired = round
                self.room.round = Round(phase="cleanup")
                self.room.revision += 1
            if close:
                self.room.closing = True
        if close:
            await self.context.parties.begin_close(GAME)
        if not self.cleanup or self.cleanup.done():
            self.cleanup = asyncio.create_task(self.finish_cleanup())
        return {"status": "closing" if close else "resetting"}

    async def finish_cleanup(self):
        if self.work and not self.work.done():
            self.work.cancel()
            await asyncio.gather(self.work, return_exceptions=True)
        if self.inference and not self.inference.done():
            await asyncio.gather(asyncio.shield(self.inference), return_exceptions=True)
        if await self.refresh_guard():
            return
        retired = self.retired
        if retired:
            await asyncio.to_thread(shutil.rmtree, self.media_root / retired.id, True)
        async with self.lock:
            if not self.room:
                return
            close = self.room.closing
            if close:
                self.room = None
            else:
                self.room.round = Round()
                self.room.revision += 1
            self.retired = None
        if close:
            await self.context.parties.finish_close(GAME)

    async def shutdown(self):
        if self.work and not self.work.done():
            self.work.cancel()
            await asyncio.gather(self.work, return_exceptions=True)
        if self.cleanup and not self.cleanup.done():
            await asyncio.gather(self.cleanup, return_exceptions=True)
        if self.inference and not self.inference.done():
            await asyncio.gather(self.inference, return_exceptions=True)
        self.room = None
        await asyncio.to_thread(shutil.rmtree, self.media_root, True)
