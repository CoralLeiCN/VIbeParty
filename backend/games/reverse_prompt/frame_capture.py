"""Encode decoded SDK frames without a browser or the optional recording service."""

import asyncio
import threading
from collections import deque
from pathlib import Path

from .media import MAX_OUTPUT

FPS = 24
FRAME_COUNT = 5 * FPS
QUEUE_LIMIT = 16
MAX_FRAME_BYTES = 1280 * 768 * 4


class FrameCapture:
    def __init__(self):
        self.loop = asyncio.get_running_loop()
        self.lock = threading.Lock()
        self.ready = asyncio.Event()
        self.queue = deque()
        self.accepting = False
        self.error = None
        self.dimensions = None
        self.received = 0
        self.encoded = 0
        self.identities = set()
        self.first_timestamp = None
        self.last_timestamp = None
        self.timestamp_span_us = 0
        self.process = None

    def start(self):
        with self.lock:
            self.accepting = True

    def stop(self):
        with self.lock:
            self.accepting = False
            self.queue.clear()

    def on_frame(self, bgra, width, height, frame_id, timestamp_us, _user_data):
        # The pinned SDK supplies immutable bytes on its native delivery thread.
        # Never move full frames into asyncio's unbounded callback queue.
        with self.lock:
            if not self.accepting:
                return
            try:
                if (
                    width <= height
                    or height <= 0
                    or width % 2
                    or height % 2
                    or len(bgra) != width * height * 4
                    or len(bgra) > MAX_FRAME_BYTES
                ):
                    raise ValueError("Invalid decoded landscape frame")
                size = (width, height)
                if self.dimensions is not None and self.dimensions != size:
                    raise ValueError("Video dimensions changed during capture")
                # Zero means absent metadata in SDK 1.5.1, not one repeated frame.
                identity = (
                    ("id", frame_id)
                    if frame_id
                    else ("timestamp", timestamp_us)
                    if timestamp_us
                    else None
                )
                if identity is not None and identity in self.identities:
                    return
                if timestamp_us:
                    if self.first_timestamp is None:
                        self.first_timestamp = timestamp_us
                    if self.last_timestamp is not None and timestamp_us < self.last_timestamp:
                        raise ValueError("Video frames arrived out of order")
                    self.timestamp_span_us = timestamp_us - self.first_timestamp
                    if self.timestamp_span_us > 15_000_000:
                        raise ValueError("Source capture exceeded fifteen seconds")
                    self.last_timestamp = timestamp_us
                if len(self.queue) >= QUEUE_LIMIT:
                    raise ValueError("Video capture could not keep up with the stream")
                self.dimensions = size
                if identity is not None:
                    self.identities.add(identity)
                self.queue.append(bgra)
                self.received += 1
                if self.received == FRAME_COUNT:
                    self.accepting = False
            except (TypeError, ValueError) as exc:
                self.error = exc
                self.accepting = False
        self.loop.call_soon_threadsafe(self.ready.set)

    async def next_frame(self):
        while True:
            self.ready.clear()
            with self.lock:
                if self.error is not None:
                    raise self.error
                if self.queue:
                    return self.queue.popleft()
            await self.ready.wait()

    async def record(self, destination: Path) -> Path:
        try:
            first = await self.next_frame()
            width, height = self.dimensions
            # Launch is retained even if cancellation races subprocess creation.
            launch = asyncio.create_task(
                asyncio.create_subprocess_exec(
                    "ffmpeg",
                    "-nostdin",
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
                    str(FPS),
                    "-i",
                    "pipe:0",
                    "-an",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-pix_fmt",
                    "yuv420p",
                    "-frames:v",
                    str(FRAME_COUNT),
                    "-movflags",
                    "+faststart",
                    "-map_metadata",
                    "-1",
                    "-fs",
                    str(MAX_OUTPUT),
                    str(destination),
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
            )
            try:
                self.process = await asyncio.shield(launch)
            except asyncio.CancelledError:
                self.process = await launch
                raise
            current = first
            for index in range(FRAME_COUNT):
                if index:
                    current = await self.next_frame()
                self.process.stdin.write(current)
                await self.process.stdin.drain()
                self.encoded += 1
            self.process.stdin.close()
            await self.process.stdin.wait_closed()
            if await self.process.wait():
                raise ValueError("Video encoding failed")
            if not 0 < destination.stat().st_size < MAX_OUTPUT:
                raise ValueError("Captured video exceeds the media limit")
            return destination
        finally:
            self.stop()
            if self.process is not None and self.process.returncode is None:
                self.process.kill()
                await self.process.wait()

    def evidence(self):
        return {
            "capture_method": "decoded_frames",
            "frames": self.received,
            "encoded_frames": self.encoded,
            "fps": FPS,
            "source_timestamp_span_us": self.timestamp_span_us,
        }
