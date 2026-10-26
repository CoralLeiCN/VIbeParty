"""Bounded conversion and probe; source media is never public."""

import asyncio
from pathlib import Path

from backend.shared.media import probe_media, run_command

MAX_SOURCE = 100 * 1024 * 1024
MAX_OUTPUT = 10 * 1024 * 1024


async def command(*args: str) -> bytes:
    return await run_command(*args)


async def probe(path: Path) -> dict:
    return await probe_media(path, "ffprobe", command)


async def prepare(source: Path, destination: Path) -> dict:
    async with asyncio.timeout(20):
        if not 0 < source.stat().st_size <= MAX_SOURCE:
            raise ValueError("Source exceeds the media limit")
        info = await probe(source)
        video = next(s for s in info["streams"] if s["codec_type"] == "video")
        duration = float(info["format"]["duration"])
        if not 5 <= duration <= 15 or video["width"] <= video["height"]:
            raise ValueError("Not enough usable landscape video")
        await command(
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-y",
            "-i",
            str(source),
            "-t",
            "5",
            "-map",
            "0:v:0",
            "-an",
            "-map_metadata",
            "-1",
            "-map_chapters",
            "-1",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            "-r",
            "24",
            "-movflags",
            "+faststart",
            "-fs",
            str(MAX_OUTPUT),
            str(destination),
        )
        return await validate(destination)


async def validate(destination: Path) -> dict:
    """Both downloaded media and locally encoded SDK frames use this publication gate."""
    async with asyncio.timeout(20):
        output = await probe(destination)
        stream = output["streams"][0]
        if (
            len(output["streams"]) != 1
            or stream["codec_name"] != "h264"
            or stream["pix_fmt"] != "yuv420p"
            or stream["width"] <= stream["height"]
            or not 4.95 <= float(output["format"]["duration"]) <= 5.05
            or not 0 < destination.stat().st_size < MAX_OUTPUT
        ):
            raise ValueError("Invalid prepared video")
        await command(
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-xerror",
            "-i",
            str(destination),
            "-f",
            "null",
            "-",
        )
        return {
            "duration": float(output["format"]["duration"]),
            "width": stream["width"],
            "height": stream["height"],
            "bytes": destination.stat().st_size,
        }
