"""Create three original geometric five-second clips, without provider calls."""

import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from backend.games.reverse_prompt.rehearsal import FIXTURES

FIXTURES.mkdir(parents=True, exist_ok=True)
y, x = np.mgrid[:384, :640]
for scene in range(3):
    output = FIXTURES / f"scene-{scene}.mp4"
    process = subprocess.Popen(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            "640x384",
            "-r",
            "24",
            "-i",
            "pipe:0",
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output),
        ],
        stdin=subprocess.PIPE,
    )
    for frame in range(120):
        image = np.full((384, 640, 3), [226, 238, 249], dtype=np.uint8)
        image[y > 342] = [127, 166, 157]
        buildings = (
            [(385, 130, 90)] if scene < 2 else [(65, 250, 80), (225, 210, 80), (410, 240, 100)]
        )
        for left, top, width in buildings:
            image[(x >= left) & (x < left + width) & (y >= top) & (y <= 342)] = [51, 90, 161]
            for wy in range(top + 20, 320, 35):
                image[(x >= left + 15) & (x < left + width - 15) & (y >= wy) & (y < wy + 10)] = [
                    191,
                    215,
                    239,
                ]
        cx = 150 + frame * 1.5 if scene < 2 else 320
        cy = 170 - frame * 0.4 if scene < 2 else 170 - frame * 0.6
        radius = 31 if scene < 2 else 51
        image[(x - cx) ** 2 + (y - cy) ** 2 <= radius**2] = (
            [228, 68, 89] if scene == 0 else [221, 127, 170]
        )
        if scene < 2:
            image[(abs(x - cx) < 1.5) & (y > cy + radius) & (y < cy + radius + 65)] = [89, 93, 113]
        process.stdin.write(image.tobytes())
    process.stdin.close()
    assert process.wait() == 0
    print(output.name)
