"""One continuously played story, with timed category updates and a saved replay."""

import asyncio
import contextlib
import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Protocol

from .domain import CATEGORIES, FIXTURE_TEXT, Clip

STYLE = (
    "Playful illustrated scene, wide fixed camera, minimal camera movement. "
    "Preserve the established setting and the same character appearance. "
    "Apply the action to the existing character. Add only the current idea. "
)
Update = Callable[[int, float], Awaitable[None]]


def scene_prompt(texts: list[str], index: int) -> str:
    # Preserve accepted text and include only facts through this category.
    return STYLE + "\n".join(
        f"{CATEGORIES[i]}: {text}" for i, text in enumerate(texts[: index + 1])
    )


class Provider(Protocol):
    recording: Clip | None

    async def run(self, texts: list[str], directory: Path, update: Update) -> Clip: ...
    async def close(self) -> bool: ...


async def checked_process(*args: str, timeout: float = 10) -> bytes:
    process = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
    )
    try:
        output, _ = await asyncio.wait_for(process.communicate(), timeout)
        if process.returncode:
            raise ValueError("media_processing_failed")
        return output
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()


async def probe_recording(path: Path) -> Clip:
    if not path.is_file() or not 0 < path.stat().st_size <= 80 * 1024 * 1024:
        raise ValueError("invalid_recording_size")
    raw = await checked_process(
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)
    )
    data = json.loads(raw)
    streams = data["streams"]
    if len(streams) != 1 or streams[0]["codec_name"] != "h264":
        raise ValueError("invalid_media_format")
    video = streams[0]
    duration = float(data["format"]["duration"])
    if video["pix_fmt"] != "yuv420p" or not 0 < duration <= 180:
        raise ValueError("invalid_recording_duration")
    if video["width"] <= 0 or video["height"] <= 0:
        raise ValueError("invalid_dimensions")
    return Clip(path, duration, video["width"], video["height"])


def hls_arguments(directory: Path) -> list[str]:
    return [
        "-f",
        "hls",
        "-hls_time",
        "1",
        "-hls_list_size",
        "0",
        "-hls_playlist_type",
        "event",
        "-hls_flags",
        "independent_segments+temp_file",
        "-hls_segment_filename",
        str(directory / "segment%04d.ts"),
        str(directory / "index.m3u8"),
    ]


async def save_recording(directory: Path) -> Clip:
    destination = directory / "story.mp4"
    await checked_process(
        "ffmpeg",
        "-v",
        "error",
        "-y",
        "-i",
        str(directory / "index.m3u8"),
        "-an",
        "-c:v",
        "copy",
        "-movflags",
        "+faststart",
        str(destination),
        timeout=15,
    )
    return await probe_recording(destination)


class FixtureProvider:
    """Stream the single WW-CAT-01 scripted video at playback speed."""

    recording: Clip | None = None

    def __init__(self):
        self.process = None

    async def run(self, texts: list[str], directory: Path, update: Update) -> Clip:
        if tuple(texts) != FIXTURE_TEXT:
            raise ValueError("fixture_text_mismatch")
        directory.mkdir(parents=True, exist_ok=True)
        source = Path(__file__).parent / "fixtures" / "story.mp4"
        self.process = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-re",
            "-i",
            str(source),
            "-an",
            "-c:v",
            "copy",
            *hls_arguments(directory),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            # Only published segments are available to the browser. No future media URLs.
            while not (directory / "index.m3u8").exists():
                if self.process.returncode is not None:
                    raise ValueError("fixture_stream_failed")
                await asyncio.sleep(0.05)
            await update(0, 0)
            for index in range(1, 4):
                while not (directory / f"segment{index * 6:04d}.ts").exists():
                    if self.process.returncode is not None:
                        raise ValueError("fixture_stream_failed")
                    await asyncio.sleep(0.05)
                await update(index, index * 6)
            if await self.process.wait():
                raise ValueError("fixture_stream_failed")
            self.recording = await save_recording(directory)
            return self.recording
        finally:
            await self._stop()
            if self.recording is None and (directory / "index.m3u8").exists():
                with contextlib.suppress(Exception):
                    self.recording = await save_recording(directory)

    async def _stop(self) -> None:
        if self.process and self.process.returncode is None:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), 3)
            except TimeoutError:
                self.process.kill()
                await self.process.wait()

    async def close(self) -> bool:
        await self._stop()
        return True
