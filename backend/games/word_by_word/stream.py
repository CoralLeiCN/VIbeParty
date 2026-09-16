"""Bounded frame bridge from Reactor to one HLS stream and MP4 recording."""

import asyncio
import contextlib
import threading
import time
from pathlib import Path

from .providers import hls_arguments, save_recording


class StreamCapture:
    fps = 24

    def __init__(self, directory: Path):
        self.directory = directory
        self.lock = threading.Lock()
        self.latest: tuple[bytes, int, int] | None = None
        self.received_at = 0.0
        self.frames = 0
        self.stopping = False
        self.process = None
        self.task = None
        self.failure: str | None = None

    @property
    def seconds(self):
        return self.frames / self.fps

    def accept(self, pixels, width, height, *_metadata):
        # Native callbacks keep one frame: bursts cannot grow memory without bound.
        with self.lock:
            if self.stopping:
                return
            if not 0 < width <= 1920 or not 0 < height <= 1080:
                self.failure = "invalid_stream_dimensions"
                return
            if len(pixels) != width * height * 4:
                self.failure = "invalid_stream_frame"
                return
            if self.latest and (width, height) != self.latest[1:]:
                self.failure = "stream_dimensions_changed"
                return
            self.latest = (bytes(pixels), width, height)
            self.received_at = time.monotonic()

    async def write(self):
        started = time.monotonic()
        while not self.stopping:
            if self.failure:
                raise RuntimeError(self.failure)
            with self.lock:
                current, received = self.latest, self.received_at
            if current is None:
                if time.monotonic() - started > 30:
                    raise TimeoutError("no_video_received")
                await asyncio.sleep(0.01)
                continue
            if time.monotonic() - received > 10:
                raise TimeoutError("video_stream_stalled")
            pixels, width, height = current
            if self.process is None:
                self.directory.mkdir(parents=True, exist_ok=True)
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
                    str(self.fps),
                    "-i",
                    "pipe:0",
                    "-an",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "ultrafast",
                    "-tune",
                    "zerolatency",
                    "-pix_fmt",
                    "yuv420p",
                    "-g",
                    str(self.fps),
                    "-sc_threshold",
                    "0",
                    "-b:v",
                    "2500k",
                    "-maxrate",
                    "3000k",
                    "-bufsize",
                    "6000k",
                    *hls_arguments(self.directory),
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                started = time.monotonic()
            self.process.stdin.write(pixels)
            await asyncio.wait_for(self.process.stdin.drain(), 5)
            self.frames += 1
            # Pace the output, repeating the latest frame during short source gaps.
            await asyncio.sleep(max(0, started + self.seconds - time.monotonic()))

    def start(self):
        self.task = asyncio.create_task(self.write())

    def check(self):
        if self.task and self.task.done():
            self.task.result()
            raise RuntimeError("video_stream_ended")

    async def wait_until(self, seconds: float):
        while self.seconds < seconds:
            self.check()
            await asyncio.sleep(0.02)

    async def ready(self):
        while not (self.directory / "index.m3u8").exists():
            self.check()
            await asyncio.sleep(0.02)

    async def finish(self):
        await self.stop()
        return await save_recording(self.directory)

    async def stop(self):
        self.stopping = True
        if self.task:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
        if self.process and self.process.returncode is None:
            self.process.stdin.close()
            try:
                await asyncio.wait_for(self.process.wait(), 5)
            except TimeoutError:
                self.process.kill()
                await self.process.wait()
        # FFmpeg writes ENDLIST when stdin closes normally, including partial stories.
        if self.process and self.process.returncode:
            with contextlib.suppress(FileNotFoundError):
                (self.directory / "story.mp4").unlink()
