import asyncio
import json
from pathlib import Path


async def command(*args: str, timeout: float = 20) -> bytes:
    process = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout)
        if process.returncode:
            raise ValueError("Media preparation failed")
        return stdout
    except BaseException:
        if process.returncode is None:
            process.kill()
        await process.wait()
        raise


async def probe(path: Path, ffprobe: str) -> dict:
    return json.loads(
        await command(
            ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)
        )
    )


async def prepare(source: Path, target: Path, ffmpeg: str, ffprobe: str) -> None:
    async with asyncio.timeout(20):
        if source.stat().st_size > 100 * 1024 * 1024:
            raise ValueError("Source exceeds limit")
        info = await probe(source, ffprobe)
        videos = [s for s in info["streams"] if s["codec_type"] == "video"]
        if not videos or float(videos[0].get("duration", info["format"].get("duration", 0))) < 4.96:
            raise ValueError("Recording is shorter than five seconds")
        await command(
            ffmpeg,
            "-y",
            "-v",
            "error",
            "-i",
            str(source),
            "-map",
            "0:v:0",
            "-t",
            "5",
            "-an",
            "-vf",
            "setpts=PTS-STARTPTS,scale=1280:768,setsar=1",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(target),
        )
        info = await probe(target, ffprobe)
        video = info["streams"][0]
        if (
            len(info["streams"]) != 1
            or video["codec_name"] != "h264"
            or video["pix_fmt"] != "yuv420p"
            or video["width"] != 1280
            or video["height"] != 768
            or not 4.96 <= float(info["format"]["duration"]) <= 5.08
            or target.stat().st_size > 20 * 1024 * 1024
        ):
            target.unlink(missing_ok=True)
            raise ValueError("Prepared clip failed validation")
