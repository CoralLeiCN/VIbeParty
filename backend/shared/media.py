"""Media process execution and probing; conversion policies belong to each game."""

import asyncio
import json
from collections.abc import Awaitable, Callable
from pathlib import Path


async def run_command(
    *args: str,
    timeout: float | None = None,
    stderr: int = asyncio.subprocess.DEVNULL,
    error_message: str = "Video preparation failed",
) -> bytes:
    process = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=stderr
    )
    try:
        communication = process.communicate()
        output, _ = (
            await communication
            if timeout is None
            else await asyncio.wait_for(communication, timeout)
        )
        if process.returncode:
            raise ValueError(error_message)
        return output
    finally:
        if process.returncode is None:
            process.kill()
        await process.wait()


async def probe_media(path: Path, ffprobe: str, command: Callable[..., Awaitable[bytes]]) -> dict:
    return json.loads(
        await command(
            ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)
        )
    )
