"""One fresh MiniMax FastH3 session per prompt, with independently proven closure."""

import asyncio
import time
from pathlib import Path
from urllib.parse import quote

import httpx

from .frame_capture import FrameCapture
from .media import validate
from .quota import Quota

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
    def __init__(self, key: str, quota: Quota):
        self.key = key
        self.quota = quota
        self.last_evidence: dict = {}

    async def generate(self, prompt: str, directory: Path, step: int) -> Path:
        from reactor_sdk import Reactor

        directory.mkdir(parents=True, exist_ok=True)
        output = directory / "video.mp4"
        started = time.monotonic()
        attempt = await asyncio.to_thread(self.quota.consume)
        self.last_evidence = {"attempt": attempt, "closed": False, "model": MODEL}
        reactor = None
        jwt = None
        sid = None
        connected = False
        published = False
        sid_tasks = []
        capture = FrameCapture(expected_dimensions=(1344, 768))
        playback = ClipPlayback(capture)
        capture_task = None

        def on_session(value):
            nonlocal sid
            if value:
                sid = value
                sid_tasks.append(
                    asyncio.create_task(asyncio.to_thread(self.quota.session, attempt, value))
                )

        async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
            try:
                async with asyncio.timeout(90):
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
                                        "max_session_duration_seconds": 90,
                                    },
                                }
                            ]
                        },
                    )
                    response.raise_for_status()
                    jwt = response.json()["jwt"]
                    if not isinstance(jwt, str) or not jwt:
                        raise GenerationError("Missing provider token")
                    reactor = Reactor(model_name=MODEL, jwt=jwt)
                    reactor.on("session_id_changed", on_session)
                    reactor.on("message", playback.message)
                    reactor.on("error", lambda _error: playback.fail("Provider session failed"))
                    reactor.track("main_video").on_raw_frame(capture.on_frame)
                    await reactor.connect()
                    connected = True
                    sid = sid or reactor.session_id
                    if not sid:
                        raise GenerationError("No provider session identity")
                    await asyncio.to_thread(self.quota.session, attempt, sid)
                    if sid_tasks:
                        await asyncio.gather(*sid_tasks)
                    for name, data, ack in (
                        ("set_autoplay", {"enabled": False}, "autoplay_accepted"),
                        ("set_canvas", {"aspect": "16:9"}, "canvas_accepted"),
                        ("set_flush_on_clip_end", {"enabled": True}, "flush_accepted"),
                    ):
                        await playback.command(reactor, name, data, ack)
                    self.last_evidence["startup_seconds"] = round(time.monotonic() - started, 3)
                    # A fresh session and text-only request give each relay its own scene.
                    reply = await playback.command(
                        reactor,
                        "enqueue",
                        {
                            "prompt": prompt + "\n\n" + INSTRUCTION,
                            "seconds": SOURCE_SECONDS,
                            "metadata": attempt,
                        },
                        "clip_queued",
                    )
                    queued = clip_info(reply)
                    if queued.get("metadata", attempt) != attempt:
                        raise GenerationError("Provider acknowledged a different clip")
                    source_frames(queued)
                    metadata_source = await playback.ready(reactor, queued)
                    self.last_evidence.update(
                        frame_metadata_source=metadata_source,
                        source_frames=SOURCE_FRAMES,
                        source_seconds=SOURCE_FRAMES / 24,
                        generated_seconds=round(time.monotonic() - started, 3),
                    )
                    capture_task = asyncio.create_task(capture.record(output))
                    playback.play_requested = True
                    # Capture starts only on this clip's matching clip_started event.
                    await playback.command(reactor, "play", {"clip_id": queued["clip_id"]})
                    await playback.wait(capture_task)
                    # End GPU use as soon as 120 frames of the ready clip are saved.
                    await self._close(reactor, client, jwt, sid, attempt)
                    reactor.close()
                    reactor = None
                    metadata = await validate(output)
                    self.last_evidence.update(metadata, **capture.evidence())
                    published = True
                    return output
            finally:
                capture.stop()
                if capture_task is not None:
                    if not capture_task.done():
                        capture_task.cancel()
                    await asyncio.gather(capture_task, return_exceptions=True)
                if reactor is not None:
                    try:
                        await self._close(reactor, client, jwt, sid, attempt)
                    except (Exception, asyncio.CancelledError):
                        pass  # Uncertain closure deliberately retains the persistent guard.
                    reactor.close()
                if sid_tasks:
                    await asyncio.gather(*sid_tasks, return_exceptions=True)
                if not published:
                    output.unlink(missing_ok=True)
                self.last_evidence.update(
                    connected=connected,
                    playback_started=playback.started,
                    total_seconds=round(time.monotonic() - started, 3),
                    **capture.evidence(),
                )

    async def _close(self, reactor, client, jwt, sid, attempt):
        async with asyncio.timeout(12):
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
