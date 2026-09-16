"""Explicit setup for public model assets. Never initializes paid allowances."""

import shutil
import subprocess
import sys

from backend.shared.config import ROOT, Settings


def run(script, *arguments):
    subprocess.run([sys.executable, str(script), *map(str, arguments)], cwd=ROOT, check=True)


def main():
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise SystemExit("Install FFmpeg and ffprobe first (macOS: brew install ffmpeg).")
    settings = Settings()
    model_setup = ROOT / "scripts/games/reverse-prompt/model_setup.py"
    if model_setup.is_file():
        model = settings.embedding_model_path
        if not (model / "vibeparty-model.json").is_file():
            run(model_setup, model)
        run(ROOT / "scripts/games/reverse-prompt/offline_check.py", model)
    print("Game assets prepared. No provider sessions or paid allowances were created.")


if __name__ == "__main__":
    main()
