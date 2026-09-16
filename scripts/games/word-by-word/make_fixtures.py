"""Render one deterministic WW-CAT-01 rehearsal story. No provider calls."""

import math
import subprocess
from pathlib import Path

W, H, FPS = 640, 360, 24


def rect(p, x, y, w, h, color):
    x0, x1 = max(0, int(x)), min(W, int(x + w))
    y0, y1 = max(0, int(y)), min(H, int(y + h))
    if x1 <= x0:
        return
    row = bytes(color) * (x1 - x0)
    for yy in range(y0, y1):
        p[(yy * W + x0) * 3 : (yy * W + x1) * 3] = row


def ellipse(p, x, y, rx, ry, color):
    for yy in range(max(0, int(y - ry)), min(H, int(y + ry) + 1)):
        span = rx * math.sqrt(max(0, 1 - ((yy - y) / ry) ** 2))
        rect(p, x - span, yy, span * 2 + 1, 1, color)


def triangle(p, x, y, w, h, color):
    for dy in range(h):
        span = w * dy / h / 2
        rect(p, x - span, y + dy, span * 2 + 1, 1, color)


def frame(step, t):
    p = bytearray(bytes((21, 30, 56)) * (W * H))
    ellipse(p, 488, 62, 30, 30, (255, 226, 162))
    ellipse(p, 478, 55, 29, 29, (21, 30, 56))
    for i in range(35):
        x = (i * 97 + 41) % W
        y = (i * 43 + 19) % 175
        rect(p, x, y, 2, 2, (155, 179, 199))
    ellipse(p, 310, 365, 400, 122, (36, 70, 68))
    for i, x in enumerate([25, 99, 160, 530, 610]):
        y = 70 + (i % 2) * 22
        rect(p, x - 7, y + 40, 14, 225, (39, 51, 64))
        triangle(p, x, y, 120, 155, (43, 88, 85))
        triangle(p, x, y + 45, 145, 145, (35, 78, 78))
    ellipse(p, 320, 300, 180, 34, (79, 101, 88))
    if step >= 1:
        bob = math.sin(t * 2) * 6 if step >= 2 else math.sin(t * 2) * 2
        x = 320 + (math.sin(t * 1.5) * 25 if step >= 2 else 0)
        y = 233 + bob
        ellipse(p, x - 39, y + 20, 44, 20, (226, 122, 67))
        ellipse(p, x - 72, y + 20, 17, 14, (249, 231, 197))
        ellipse(p, x, y + 15, 23, 38, (226, 122, 67))
        ellipse(p, x + 4, y + 16, 13, 26, (253, 221, 173))
        stride = math.sin(t * 2) * 19 if step >= 2 else 7
        rect(p, x - 16 - stride, y + 42, 13, 21, (57, 40, 46))
        rect(p, x + 6 + stride, y + 42, 13, 21, (57, 40, 46))
        ellipse(p, x, y - 29, 31, 27, (235, 136, 76))
        triangle(p, x - 19, y - 74, 22, 34, (235, 136, 76))
        triangle(p, x + 19, y - 74, 22, 34, (235, 136, 76))
        triangle(p, x - 19, y - 69, 11, 22, (77, 47, 54))
        triangle(p, x + 19, y - 69, 11, 22, (77, 47, 54))
        ellipse(p, x, y - 15, 18, 11, (255, 224, 180))
        ellipse(p, x, y - 23, 5, 4, (44, 37, 53))
        ellipse(p, x - 12, y - 35, 3, 4, (44, 37, 53))
        ellipse(p, x + 12, y - 35, 3, 4, (44, 37, 53))
        rect(p, x - 20, y - 59, 40, 8, (250, 198, 54))
        for point in [-15, 0, 15]:
            triangle(p, x + point, int(y - 78), 15, 20, (250, 198, 54))
        if step >= 2:
            ellipse(p, x, y + 34, 36, 8, (239, 172, 206))
    if step >= 3:
        colors = [(215, 246, 255), (255, 255, 255), (191, 229, 253), (222, 255, 242)]
        for i in range(90):
            x = (i * 103 + math.sin(t * 2 + i) * 22) % W
            y = (i * 41 + t * 58) % H
            ellipse(p, x, y, 3, 3, colors[i % 4])
    # The UI supplies the accessible label. The coral band identifies these scripted assets.
    rect(p, 0, 350, W, 10, (220, 122, 98))
    return p


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("output", type=Path)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for filename in ["story.mp4"]:
        path = args.output / filename
        proc = subprocess.Popen(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-f",
                "rawvideo",
                "-pixel_format",
                "rgb24",
                "-video_size",
                f"{W}x{H}",
                "-framerate",
                str(FPS),
                "-i",
                "pipe:0",
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "23",
                "-pix_fmt",
                "yuv420p",
                "-g",
                str(FPS),
                "-sc_threshold",
                "0",
                "-movflags",
                "+faststart",
                str(path),
            ],
            stdin=subprocess.PIPE,
        )
        for n in range(FPS * 24):
            proc.stdin.write(frame(n // (FPS * 6), n / FPS))
        proc.stdin.close()
        if proc.wait():
            raise RuntimeError("FFmpeg failed")
        print(path)


if __name__ == "__main__":
    main()
