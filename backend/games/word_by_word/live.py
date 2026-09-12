"""FastH3's four-step predecessor chain. Live admission stays gated on measured capture.

The frame/event boundary policy requires a real laptop spike before enabling play.
No local SDK status or disconnect acknowledgment can clear the closure guard alone.
"""

import asyncio
import contextlib
import json
import queue
import threading
import time
from pathlib import Path
from urllib.parse import quote

import httpx
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.shared.config import ROOT

from .domain import Clip
from .providers import probe_clip, scene_prompt

API = "https://api.reactor.inc"
MODEL = "reactor/fast-h3"
SESSION_HEADERS = {"Reactor-API-Version": "1", "Reactor-API-Accept-Version": "1"}
MAX_BYTES = 20 * 1024 * 1024


class LiveSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    reactor_api_key: SecretStr = SecretStr("")
    word_by_word_live_enabled: bool = False
    word_by_word_capture_verified: bool = False
    word_by_word_prompt_limit_verified: bool = False
    word_by_word_live_slot: str = ""
    word_by_word_previous_session_closed: bool = False

    def unavailable_reason(self) -> str | None:
        if not self.word_by_word_live_enabled or not self.word_by_word_capture_verified:
            return "FastH3 live verification is pending. Use the fixture rehearsal."
        if not self.word_by_word_prompt_limit_verified:
            return "FastH3’s full contribution limit still needs verification."
        if not self.word_by_word_live_slot or not self.word_by_word_previous_session_closed:
            return "The presenter must confirm the live trial slot and previous session closure."
        key = self.reactor_api_key.get_secret_value()
        if not key.startswith("rk_"):
            return "The presenter must configure the Reactor credential before live play."
        return None


class CaptureError(RuntimeError):
    pass


class FrameCapture:
    """A bounded native-thread-to-FFmpeg queue; overflow invalidates the capture."""

    def __init__(self, destination: Path, expected_frames: int):
        if not 124 <= expected_frames <= 175:
            raise CaptureError("unexpected_clip_length")
        self.destination = destination
        self.expected = expected_frames
        self.frames: queue.Queue = queue.Queue(maxsize=8)
        self.lock = threading.Lock()
        self.accepting = False
        self.closed = False
        self.error: str | None = None
        self.received = 0
        self.first_id: int | None = None
        self.last_id: int | None = None
        self.first_timestamp: int | None = None
        self.last_timestamp: int | None = None
        self.dimensions: tuple[int, int] | None = None
        self.finished = asyncio.Event()
        self.process: asyncio.subprocess.Process | None = None
        self.task: asyncio.Task | None = None

    def accept(
        self, bgra: bytes, width: int, height: int, frame_id: int, timestamp: int, metadata: bytes
    ) -> None:
        # Do not enqueue an unbounded call_soon_threadsafe callback for every frame.
        with self.lock:
            if not self.accepting or self.closed or self.received >= self.expected or self.error:
                return
            if not 0 < width <= 1920 or not 0 < height <= 1080 or len(bgra) != width * height * 4:
                self.error = "invalid_frame"
                return
            if self.dimensions and self.dimensions != (width, height):
                self.error = "dimensions_changed"
                return
            if self.last_id is not None and frame_id <= self.last_id:
                self.error = "non_monotonic_frame_ids"
                return
            self.dimensions = (width, height)
            try:
                self.frames.put_nowait(bgra)
            except queue.Full:
                self.error = "frame_queue_overflow"
                return
            self.received += 1
            if self.first_id is None:
                self.first_id, self.first_timestamp = frame_id, timestamp
            self.last_id, self.last_timestamp = frame_id, timestamp

    async def write(self) -> Clip:
        self.destination.parent.mkdir(parents=True, exist_ok=True)
        partial = self.destination.with_suffix(".partial.mp4")
        written = 0
        try:
            while written < self.expected:
                if self.error:
                    raise CaptureError(self.error)
                try:
                    frame = self.frames.get_nowait()
                except queue.Empty:
                    await asyncio.sleep(0.005)
                    continue
                if self.process is None:
                    width, height = self.dimensions
                    self.process = await asyncio.create_subprocess_exec(
                        "ffmpeg",
                        "-v",
                        "error",
                        "-y",
                        "-f",
                        "rawvideo",
                        "-pixel_format",
                        "bgra",
                        "-video_size",
                        f"{width}x{height}",
                        "-framerate",
                        "24",
                        "-i",
                        "pipe:0",
                        "-an",
                        "-c:v",
                        "libx264",
                        "-preset",
                        "ultrafast",
                        "-pix_fmt",
                        "yuv420p",
                        "-movflags",
                        "+faststart",
                        "-fs",
                        str(MAX_BYTES),
                        str(partial),
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL,
                    )
                self.process.stdin.write(frame)
                await self.process.stdin.drain()
                written += 1
            # clip_finished is a sender boundary. Both all frames and this exact clip's
            # finish are required; receiving finish early does not cut buffered video.
            await self.finished.wait()
            if self.error:
                raise CaptureError(self.error)
            self.process.stdin.close()
            await self.process.wait()
            if self.process.returncode:
                raise CaptureError("encode_failed")
            clip = await probe_clip(partial, self.expected)
            if (clip.width, clip.height) != self.dimensions:
                raise CaptureError("capture_dimensions_changed")
            partial.replace(self.destination)
            clip.path = self.destination
            return clip
        finally:
            with self.lock:
                self.closed = True
                self.accepting = False
            if self.process and self.process.returncode is None:
                self.process.kill()
                await self.process.wait()
            partial.unlink(missing_ok=True)
            while not self.frames.empty():
                with contextlib.suppress(queue.Empty):
                    self.frames.get_nowait()

    async def abort(self) -> None:
        with self.lock:
            self.closed = True
        if self.task and not self.task.done():
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)

    def evidence(self) -> dict:
        return {
            "expected_frames": self.expected,
            "received_frames": self.received,
            "first_frame_id": self.first_id,
            "last_frame_id": self.last_id,
            "first_timestamp_us": self.first_timestamp,
            "last_timestamp_us": self.last_timestamp,
            "boundary_review": "required until the laptop capture gate passes",
        }


class FastH3Provider:
    def __init__(
        self,
        key: str,
        *,
        client_factory=None,
        reactor_factory=None,
        evidence_path: Path | None = None,
    ):
        self.key = key
        self.client_factory = client_factory or (
            lambda: httpx.AsyncClient(timeout=10, follow_redirects=False)
        )
        self.reactor_factory = reactor_factory
        self.evidence_path = evidence_path
        self.reactor = None
        self.jwt: str | None = None
        self.session_id: str | None = None
        self.connect_started = False
        self.closed = False
        self.changed = asyncio.Event()
        self.failure: str | None = None
        self.generated: dict[str, dict] = {}
        self.previous = ""
        self.next_index = 0
        self.capture: FrameCapture | None = None
        self.capture_clip_id: str | None = None
        self.evidence: dict = {
            "mode": "live",
            "model": MODEL,
            "sdk": "1.5.1",
            "clips": [],
            "closed": False,
        }
        self.started_at = time.monotonic()

    @staticmethod
    def payload(message: dict) -> dict:
        data = message.get("data", message)
        if not isinstance(data, dict):
            raise CaptureError("invalid_provider_message")
        return data

    def message(self, message: dict) -> None:
        try:
            kind = message.get("type")
            data = self.payload(message)
            clip = data.get("clip", {})
            clip_id = clip.get("clip_id", data.get("clip_id"))
        except (AttributeError, CaptureError):
            self.on_error()
            return
        if kind in {"command_error", "clip_failed", "error"}:
            self.failure = "provider_rejected_generation"
        if kind == "clip_generated" and clip_id:
            if not isinstance(clip_id, str) or len(self.generated) >= 8:
                self.on_error()
                return
            self.generated[clip_id] = {"frames": clip.get("frames")}
        if kind == "clip_started" and clip_id:
            if clip_id == self.capture_clip_id and self.capture:
                # This event/frame ordering is intentionally a measured live gate.
                with self.capture.lock:
                    self.capture.accepting = True
        if kind == "clip_finished" and clip_id:
            if clip_id == self.capture_clip_id and self.capture:
                self.capture.finished.set()
        self.changed.set()

    def frame(self, bgra, width, height, frame_id, timestamp_us, user_data):
        capture = self.capture
        if capture:
            capture.accept(bgra, width, height, frame_id, timestamp_us, user_data)

    def session_changed(self, value: str | None) -> None:
        if value:
            self.session_id = value
            self.evidence["session_id"] = value

    async def open(self) -> None:
        if self.reactor or self.connect_started:
            raise CaptureError("session_already_attempted")
        async with self.client_factory() as client:
            response = await client.post(
                API + "/tokens",
                headers={"Reactor-API-Key": self.key},
                json={
                    "expires_after": 900,
                    "authorization_details": [
                        {
                            "type": "session",
                            "resources": {"models": {"match": [MODEL]}},
                            "constraints": {"max_sessions": 1, "max_session_duration_seconds": 180},
                        }
                    ],
                },
            )
            response.raise_for_status()
            self.jwt = response.json()["jwt"]
        if not isinstance(self.jwt, str) or not self.jwt:
            raise CaptureError("missing_provider_token")
        factory = self.reactor_factory
        if factory is None:
            from reactor_sdk import Reactor

            factory = Reactor
        self.reactor = factory(model_name=MODEL, jwt=self.jwt)
        self.reactor.on("session_id_changed", self.session_changed)
        self.reactor.on("message", self.message)
        self.reactor.on("error", lambda _: self.on_error())
        self.reactor.track("main_video").on_raw_frame(self.frame)
        self.connect_started = True
        await self.reactor.connect()
        self.session_changed(self.reactor.session_id)
        if not self.session_id:
            raise CaptureError("session_identity_unknown")
        for name, data, acknowledgment in (
            ("set_autoplay", {"enabled": False}, "autoplay_accepted"),
            ("set_canvas", {"aspect": "16:9"}, "canvas_accepted"),
            ("set_flush_on_clip_end", {"enabled": False}, "flush_accepted"),
        ):
            reply = await self.command(name, data)
            if not reply or reply.get("type") != acknowledgment:
                raise CaptureError("unconfirmed_session_settings")
        self.evidence["startup_seconds"] = round(time.monotonic() - self.started_at, 3)
        self.evidence["constraints"] = {"max_sessions": 1, "max_session_duration_seconds": 180}

    def on_error(self):
        self.failure = "provider_session_failed"
        self.changed.set()

    async def command(self, name: str, data: dict):
        if self.failure:
            raise CaptureError(self.failure)
        result = await self.reactor.send_command(name, data)
        if self.failure:
            raise CaptureError(self.failure)
        return result

    async def wait_generated(self, clip_id: str) -> dict:
        while True:
            self.changed.clear()
            if self.failure:
                raise CaptureError(self.failure)
            if clip_id in self.generated:
                return self.generated[clip_id]
            await self.changed.wait()

    async def capture_failure(self) -> None:
        while not self.failure:
            self.changed.clear()
            await self.changed.wait()
        raise CaptureError(self.failure)

    async def segment(self, texts: list[str], index: int, destination: Path) -> Clip:
        if index != self.next_index or not self.session_id or self.closed:
            raise CaptureError("invalid_chain_order")
        started = time.monotonic()
        reply = await self.command(
            "enqueue",
            {
                "prompt": scene_prompt(texts, index),
                "seconds": 6,
                "continue_from_clip_id": self.previous,
                "metadata": f"word-by-word-{index}",
            },
        )
        # An absent/ambiguous paid acknowledgment is never retried.
        if not reply or reply.get("type") != "clip_queued":
            raise CaptureError("ambiguous_enqueue")
        clip = self.payload(reply).get("clip", {})
        clip_id = clip.get("clip_id")
        if not clip_id or not isinstance(clip_id, str):
            raise CaptureError("missing_clip_identity")
        generated = await self.wait_generated(clip_id)
        clip = {**clip, **generated}
        frames = clip.get("frames")
        if not isinstance(frames, int):
            raise CaptureError("missing_clip_frame_count")
        capture = FrameCapture(destination, frames)
        self.capture, self.capture_clip_id = capture, clip_id
        capture.task = asyncio.create_task(capture.write())
        failed = asyncio.create_task(self.capture_failure())
        try:
            await self.command("play", {"clip_id": clip_id})
            done, _ = await asyncio.wait(
                (capture.task, failed), return_when=asyncio.FIRST_COMPLETED
            )
            if failed in done:
                await failed
            saved = await capture.task
            if self.failure:
                raise CaptureError(self.failure)
            self.previous = clip_id
            self.next_index += 1
            self.evidence["clips"].append(
                {
                    "index": index,
                    "duration": saved.duration,
                    "width": saved.width,
                    "height": saved.height,
                    "bytes": saved.path.stat().st_size,
                    "step_seconds": round(time.monotonic() - started, 3),
                    **capture.evidence(),
                }
            )
            return saved
        finally:
            failed.cancel()
            await asyncio.gather(failed, return_exceptions=True)
            await capture.abort()
            self.capture, self.capture_clip_id = None, None

    async def terminal(self, client) -> bool:
        response = await client.get(
            f"{API}/sessions/{quote(self.session_id, safe='')}",
            headers={**SESSION_HEADERS, "Authorization": f"Bearer {self.jwt}"},
        )
        if response.status_code == 404:
            return True
        response.raise_for_status()
        data = response.json()
        if data.get("session_id", self.session_id) != self.session_id:
            return False
        return data.get("state") in {"CLOSED", "INACTIVE"}

    async def close(self) -> bool:
        try:
            return await self._close()
        finally:
            self.evidence["closed"] = self.closed
            self.evidence["total_seconds"] = round(time.monotonic() - self.started_at, 3)
            if self.evidence_path:
                await asyncio.to_thread(self.write_evidence, self.evidence_path)

    async def _close(self) -> bool:
        if self.closed:
            return True
        if self.capture:
            await self.capture.abort()
        if self.reactor:
            try:
                await asyncio.wait_for(self.reactor.disconnect(), 5)
            except Exception:
                pass  # Always check independently; never interpret this as confirmation.
        if not self.connect_started:
            self.closed = True  # No request capable of opening a provider session was sent.
        elif not self.session_id or not self.jwt:
            return False  # A lost create acknowledgment requires operator resolution.
        else:
            async with self.client_factory() as client:
                if not await self.terminal(client):
                    response = await client.delete(
                        f"{API}/sessions/{quote(self.session_id, safe='')}",
                        headers={**SESSION_HEADERS, "Authorization": f"Bearer {self.jwt}"},
                    )
                    if response.status_code != 404:
                        response.raise_for_status()
                    if not await self.terminal(client):
                        return False
                self.closed = True
        if self.closed and self.reactor:
            self.reactor.close()
        return self.closed

    def write_evidence(self, destination: Path) -> None:
        # No prompts, credentials, cookie values, raw model messages or remote URLs.
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        destination.write_text(json.dumps(self.evidence, indent=2) + "\n")
        destination.chmod(0o600)
