"""Generate original, explicitly synthetic playback fixtures; no provider calls."""

import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[3]
target = root / "backend/games/prompt_royale/fixtures"
target.mkdir(parents=True, exist_ok=True)
for index in range(4):
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=1280x768:rate=24:duration=5",
            "-vf",
            f"hue=h={index * 80}",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(target / f"{index}.mp4"),
        ],
        check=True,
        timeout=30,
    )
print("Four original five-second synthetic fixture clips prepared.")
