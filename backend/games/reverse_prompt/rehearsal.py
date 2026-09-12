"""The fixed rehearsal is visibly synthetic and never stands in for live output."""

import asyncio
import shutil
from pathlib import Path

PROMPTS = [
    "A red balloon floats past a blue tower.",
    "A pink balloon floats above a blue building.",
    "A pink moon rises over a blue city.",
]
GUESSES = {"B": "A red balloon floats beside a building.", "C": "A pink moon hangs above a city."}
SAMPLE_SCORES = [88, 46]
FIXTURES = Path(__file__).parent / "fixtures"


class RehearsalProvider:
    async def generate(self, prompt: str, directory: Path, step: int) -> Path:
        if prompt != PROMPTS[step]:
            raise ValueError("Rehearsal requires the scripted scene")
        await asyncio.sleep(0.4)
        directory.mkdir(parents=True, exist_ok=True)
        output = directory / "video.mp4"
        # Tiny bundled clips: finish this copy before cancellation can release cleanup.
        shutil.copyfile(FIXTURES / f"scene-{step}.mp4", output)
        return output
