"""Independent MiniMax FastH3 clips in one bounded round session."""

import asyncio
import time
from pathlib import Path
from urllib.parse import quote

import httpx

from .frame_capture import FrameCapture
from .media import validate
from .quota import GuardError, Quota

API = "https://api.reactor.inc"
MODEL = "reactor/fast-h3"
SOURCE_SECONDS = 5.167  # The published minimum snaps to 124 frames at 24 fps.
SOURCE_FRAMES = 124
INSTRUCTION = (
    "A single continuous shot depicting the described scene. No captions or on-screen text."
)
HEADERS = {"Reactor-API-Version": "1", "Reactor-API-Accept-Version": "1"}


class GenerationError(RuntimeError):
    pass


def payload(message: dict) -> dict:
    if not isinstance(message, dict):
        raise GenerationError("Invalid provider message")
    data = message.get("data", message)
    if not isinstance(data, dict):
        raise GenerationError("Invalid provider message")
    return data


def clip_info(message: dict) -> dict:
    data = payload(message)
    clip = data.get("clip", data)
    if (
        not isinstance(clip, dict)
        or not isinstance(clip.get("clip_id"), str)
        or not 1 <= len(clip["clip_id"]) <= 200
    ):
        raise GenerationError("Missing provider clip identity")
    return clip


def source_frames(clip: dict) -> int | None:
    frames = clip.get("frames")
    if frames is None:
        return None
    if type(frames) not in {int, float} or frames != SOURCE_FRAMES:
        raise GenerationError("Unexpected generated clip length")
    return SOURCE_FRAMES


class ClipPlayback:
    """Correlate the sole submitted clip before admitting streamed frames."""

    def __init__(self, capture: FrameCapture):
        self.capture = capture
        self.failure = asyncio.get_running_loop().create_future()
        self.changed = asyncio.Event()
        self.generated = {}
        self.clip_id = None
        self.play_requested = False
        self.started = False

    def fail(self, reason="Provider rejected generation"):
        if not self.failure.done():
            self.failure.set_result(reason)

    def message(self, message):
        try:
            payload(message)
            kind = message.get("type")
            if kind in {"command_error", "clip_failed", "error"}:
                self.fail()
            elif kind == "clip_generated":
                clip = clip_info(message)
                if len(self.generated) >= 4 and clip["clip_id"] not in self.generated:
                    raise GenerationError("Unexpected provider clips")
                self.generated[clip["clip_id"]] = clip
                self.changed.set()
            elif kind in {"clip_started", "clip_finished", "clip_stopped"}:
                clip = clip_info(message)
                if not self.play_requested:
                    raise GenerationError("Unexpected provider playback")
                if clip["clip_id"] != self.clip_id:
                    raise GenerationError("Provider played a different clip")
                if kind == "clip_started" and not self.started:
                    self.started = True
                    self.capture.start()
                elif kind in {"clip_finished", "clip_stopped"}:
                    self.capture.finish()
        except GenerationError as error:
            self.fail(str(error))

    async def wait(self, task):
        """Wake even if a command is waiting for an acknowledgment that never arrives."""
        try:
            done, _ = await asyncio.wait({task, self.failure}, return_when=asyncio.FIRST_COMPLETED)
            if self.failure in done:
                raise GenerationError(self.failure.result())
            return task.result()
        finally:
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def command(self, reactor, name, data, acknowledgment=None):
        if self.failure.done():
            raise GenerationError(self.failure.result())
        result = await self.wait(asyncio.create_task(reactor.send_command(name, data)))
        if acknowledgment and (
            not isinstance(result, dict) or result.get("type") != acknowledgment
        ):
            raise GenerationError("Provider command was not confirmed")
        return result

    async def ready(self, reactor, queued):
        clip_id = queued["clip_id"]
        self.clip_id = clip_id
        while clip_id not in self.generated:
            self.changed.clear()
            await self.wait(asyncio.create_task(self.changed.wait()))
        # Compact completion events must not erase the correlated enqueue metadata.
        acknowledged = source_frames(queued)
        generated = source_frames(self.generated[clip_id])
        if generated or acknowledged:
            return "generated" if generated else "enqueue"
        # One read of the existing clip; this never repeats the paid enqueue.
        reply = await self.command(reactor, "get_queue", {}, "queue_update")
        clips = payload(reply).get("playout")
        if not isinstance(clips, list) or len(clips) > 20:
            raise GenerationError("Invalid provider queue")
        for clip in clips:
            if isinstance(clip, dict) and clip.get("clip_id") == clip_id:
                if source_frames(clip):
                    return "queue"
                break
        raise GenerationError("Missing generated clip length")


async def terminal(client, jwt: str, session_id: str) -> bool:
    response = await client.get(
        f"{API}/sessions/{quote(session_id, safe='')}",
        headers={**HEADERS, "Authorization": f"Bearer {jwt}"},
    )
    if response.status_code == 404:
        return True
    response.raise_for_status()
    data = response.json()
    return data.get("session_id", session_id) == session_id and data.get("state") in {
        "CLOSED",
        "INACTIVE",
    }


class FastH3Provider:
    """One creator session for up to three independent clips in one round."""

    SESSION_SECONDS = 360

    def __init__(self, key: str, quota: Quota):
        self.key = key
        self.quota = quota
        self.last_evidence: dict = {}
        self.lock = asyncio.Lock()
        self.reactor = None
        self.jwt = None
        self.sid = None
        self.session_attempt = None
        self.sid_tasks = []
        self.playback = None
        self.retired_ids = set()
        self.next_step = 0
        self.failure = None

    def _fail(self):
        self.last_evidence["session_error"] = "Provider session failed"
        if self.failure is not None and not self.failure.done():
            self.failure.set_result(None)
        if self.playback is not None:
            self.playback.fail("Provider session failed")

    def _message(self, message):
        # Finished clips can send late boundary events while the next one is queued.
        if isinstance(message, dict) and message.get("type") in {
            "clip_generated",
            "clip_started",
            "clip_finished",
            "clip_stopped",
            "clip_failed",
        }:
            try:
                if clip_info(message)["clip_id"] in self.retired_ids:
                    return
            except GenerationError:
                self._fail()
                return
        if self.playback is not None:
            self.playback.message(message)
        elif isinstance(message, dict) and message.get("type") in {
            "error",
            "command_error",
            "clip_failed",
            "clip_started",
        }:
            self._fail()

    def _frame(self, *args):
        playback = self.playback
        if playback is not None:
            playback.capture.on_frame(*args)

    def _session(self, value):
        if value:
            if self.sid and value != self.sid:
                self._fail()
                return
            self.sid = value
            self.sid_tasks.append(
                asyncio.create_task(
                    asyncio.to_thread(self.quota.session, self.session_attempt, value)
                )
            )

    async def wait_failure(self):
        if self.failure is None:
            raise GenerationError("Provider session is not active")
        await asyncio.shield(self.failure)
        raise GenerationError("Provider session failed")

    async def _connect(self, client, playback):
        from reactor_sdk import Reactor

        self.last_evidence["phase"] = "token"
        response = await client.post(
            API + "/tokens",
            headers={"Reactor-API-Key": self.key},
            json={
                "authorization_details": [
                    {
                        "type": "session",
                        "resources": {"models": {"match": [MODEL]}},
                        "constraints": {
                            "max_sessions": 1,
                            "max_session_duration_seconds": self.SESSION_SECONDS,
                        },
                    }
                ]
            },
        )
        response.raise_for_status()
        self.jwt = response.json()["jwt"]
        if not isinstance(self.jwt, str) or not self.jwt:
            raise GenerationError("Missing provider token")
        self.reactor = Reactor(model_name=MODEL, jwt=self.jwt)
        self.reactor.on("session_id_changed", self._session)
        self.reactor.on("message", self._message)
        self.reactor.on("error", lambda _error: self._fail())
        self.reactor.track("main_video").on_raw_frame(self._frame)
        self.last_evidence["phase"] = "connect"
        await self.reactor.connect()
        self.last_evidence["connected"] = True
        self.sid = self.sid or self.reactor.session_id
        if not self.sid:
            raise GenerationError("No provider session identity")
        await asyncio.to_thread(self.quota.session, self.session_attempt, self.sid)
        if self.sid_tasks:
            await asyncio.gather(*self.sid_tasks)
        for name, data, ack in (
            ("set_autoplay", {"enabled": False}, "autoplay_accepted"),
            ("set_canvas", {"aspect": "16:9"}, "canvas_accepted"),
            ("set_flush_on_clip_end", {"enabled": True}, "flush_accepted"),
        ):
            self.last_evidence["phase"] = name
            await playback.command(self.reactor, name, data, ack)

    async def generate(self, prompt: str, directory: Path, step: int) -> Path:
        async with self.lock:
            return await self._generate(prompt, directory, step)

    async def _generate(self, prompt: str, directory: Path, step: int) -> Path:
        if step != self.next_step or step not in {0, 1, 2}:
            raise GenerationError("Unexpected relay step")
        if step and (self.reactor is None or self.failure.done()):
            raise GenerationError("Provider session is not available")
        directory.mkdir(parents=True, exist_ok=True)
        output = directory / "video.mp4"
        started = time.monotonic()
        attempt = await asyncio.to_thread(self.quota.consume, self.session_attempt)
        if step == 0:
            self.session_attempt = attempt
            self.failure = asyncio.get_running_loop().create_future()
        self.last_evidence = {
            "attempt": attempt,
            "closed": False,
            "model": MODEL,
            "step": step,
            "session_reused": step > 0,
            "connected": step > 0,
        }
        capture = FrameCapture(expected_dimensions=(1344, 768))
        playback = ClipPlayback(capture)
        self.playback = playback
        capture_task = None
        published = False
        try:
            async with asyncio.timeout(90):
                if step == 0:
                    async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
                        await self._connect(client, playback)
                self.last_evidence["startup_seconds"] = round(time.monotonic() - started, 3)
                self.last_evidence["phase"] = "enqueue"
                # Every clip uses only its own text. Continuation and image inputs are omitted.
                reply = await playback.command(
                    self.reactor,
                    "enqueue",
                    {
                        "prompt": prompt + "\n\n" + INSTRUCTION,
                        "seconds": SOURCE_SECONDS,
                        "metadata": attempt,
                    },
                    "clip_queued",
                )
                queued = clip_info(reply)
                if (
                    queued["clip_id"] in self.retired_ids
                    or queued.get("metadata", attempt) != attempt
                ):
                    raise GenerationError("Provider acknowledged a different clip")
                source_frames(queued)
                self.last_evidence["phase"] = "wait_generated"
                metadata_source = await playback.ready(self.reactor, queued)
                self.last_evidence.update(
                    frame_metadata_source=metadata_source,
                    source_frames=SOURCE_FRAMES,
                    source_seconds=SOURCE_FRAMES / 24,
                    generated_seconds=round(time.monotonic() - started, 3),
                )
                capture_task = asyncio.create_task(capture.record(output))
                playback.play_requested = True
                self.last_evidence["phase"] = "play"
                await playback.command(self.reactor, "play", {"clip_id": queued["clip_id"]})
                self.last_evidence["phase"] = "capture"
                await playback.wait(capture_task)
                # Stop the remaining source frames before another player's input begins.
                self.last_evidence["phase"] = "stop_playback"
                await playback.command(self.reactor, "stop", {})
                self.last_evidence["phase"] = "validate"
                metadata = await validate(output)
                self.last_evidence.update(metadata, **capture.evidence())
                self.next_step += 1
                published = True
                self.last_evidence.update(phase="saved", outcome="saved")
                return output
        except asyncio.CancelledError:
            self.last_evidence["outcome"] = "cancelled"
            raise
        except Exception as error:
            self.last_evidence.update(outcome="failed", failure_category=type(error).__name__)
            if isinstance(error, GenerationError):
                self.last_evidence["failure_reason"] = str(error)
            raise
        finally:
            capture.stop()
            self.playback = None
            if playback.clip_id:
                self.retired_ids.add(playback.clip_id)
            if capture_task is not None:
                if not capture_task.done():
                    capture_task.cancel()
                await asyncio.gather(capture_task, return_exceptions=True)
            if not published:
                try:
                    await self._close_owned()
                except (Exception, asyncio.CancelledError):
                    pass  # Uncertain closure retains the persistent guard.
                output.unlink(missing_ok=True)
            self.last_evidence.update(
                playback_started=playback.started,
                total_seconds=round(time.monotonic() - started, 3),
                **capture.evidence(),
            )
            if capture.error is not None:
                self.last_evidence["capture_error"] = str(capture.error)
            await self._record_evidence(attempt)

    async def _record_evidence(self, attempt):
        try:
            await asyncio.to_thread(
                self.quota.record_outcome,
                attempt,
                {key: value for key, value in self.last_evidence.items() if key != "attempt"},
            )
        except GuardError:
            self.last_evidence["diagnostics_unavailable"] = True

    async def close(self):
        async with self.lock:
            try:
                await self._close_owned()
            finally:
                if "attempt" in self.last_evidence:
                    await self._record_evidence(self.last_evidence["attempt"])

    async def _close_owned(self):
        if self.session_attempt is None:
            return
        try:
            if self.sid_tasks:
                # A failed ledger write must not prevent terminating the actual session.
                await asyncio.gather(*self.sid_tasks, return_exceptions=True)
            async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
                await self._close(self.reactor, client, self.jwt, self.sid, self.session_attempt)
            self.last_evidence["closed"] = True
            self.session_attempt = None
            self.next_step = 0
            self.retired_ids.clear()
            self.sid_tasks.clear()
            self.sid = self.jwt = None
        finally:
            if self.reactor is not None:
                self.reactor.close()
                self.reactor = None

    async def _close(self, reactor, client, jwt, sid, attempt):
        async with asyncio.timeout(12):
            if reactor is not None:
                try:
                    await asyncio.wait_for(reactor.disconnect(), timeout=5)
                except Exception:
                    pass
            if not sid or not jwt:
                raise GenerationError("Session closure needs operator verification")
            if not await terminal(client, jwt, sid):
                response = await client.delete(
                    f"{API}/sessions/{quote(sid, safe='')}",
                    headers={**HEADERS, "Authorization": f"Bearer {jwt}"},
                )
                if response.status_code != 404:
                    response.raise_for_status()
                if not await terminal(client, jwt, sid):
                    raise GenerationError("Session closure needs operator verification")
            await asyncio.to_thread(self.quota.confirm_closed, attempt, "terminal provider GET")
            self.last_evidence["closed"] = True
