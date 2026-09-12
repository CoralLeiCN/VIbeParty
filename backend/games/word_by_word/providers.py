"""Private local fixture media and the game's narrow provider/capture boundary."""

import asyncio
import json
import shutil
from pathlib import Path
from typing import Protocol

from .domain import CATEGORIES, FIXTURE_TEXT, Clip

STYLE = (
    "Playful illustrated scene, wide fixed camera, minimal camera movement. "
    "Preserve the established setting and the same character appearance. "
    "Apply the action to the existing character. Add only the current idea. "
)


def scene_prompt(texts: list[str], index: int) -> str:
    # Callers supply accepted, unmodified text. Never include a future contribution.
    prompt = STYLE + "\n".join(
        f"{CATEGORIES[i]}: {text}" for i, text in enumerate(texts[: index + 1])
    )
    if len(prompt) > 4000:
        raise ValueError("prompt_limit")
    return prompt


class Provider(Protocol):
    async def open(self) -> None: ...
    async def segment(self, texts: list[str], index: int, destination: Path) -> Clip: ...
    async def close(self) -> bool: ...


async def checked_process(*args: str, timeout: float = 10) -> bytes:
    process = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
    )
    try:
        output, _ = await asyncio.wait_for(process.communicate(), timeout)
        if process.returncode:
            raise ValueError("media_validation_failed")
        return output
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()


async def probe_clip(path: Path, expected_frames: int | None = None) -> Clip:
    if not path.is_file() or not 0 < path.stat().st_size <= 20 * 1024 * 1024:
        raise ValueError("invalid_clip_size")
    raw = await checked_process(
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)
    )
    data = json.loads(raw)
    streams = data["streams"]
    if len(streams) != 1 or streams[0]["codec_name"] != "h264":
        raise ValueError("invalid_media_format")
    video = streams[0]
    duration = float(data["format"]["duration"])
    if video["pix_fmt"] != "yuv420p" or not 5 <= duration <= 7:
        raise ValueError("invalid_clip_duration")
    if expected_frames is not None and int(video.get("nb_frames", 0)) != expected_frames:
        raise ValueError("incomplete_capture")
    if video["width"] <= 0 or video["height"] <= 0:
        raise ValueError("invalid_dimensions")
    await checked_process("ffmpeg", "-v", "error", "-xerror", "-i", str(path), "-f", "null", "-")
    return Clip(path, duration, video["width"], video["height"])


class FixtureProvider:
    async def open(self) -> None:
        await asyncio.sleep(0.2)

    async def segment(self, texts: list[str], index: int, destination: Path) -> Clip:
        if tuple(texts) != FIXTURE_TEXT:
            raise ValueError("fixture_text_mismatch")
        source = Path(__file__).parent / "fixtures" / f"{index}.mp4"
        destination.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(shutil.copyfile, source, destination)
        await asyncio.sleep(0.45)
        return await probe_clip(destination, 144)

    async def close(self) -> bool:
        return True
