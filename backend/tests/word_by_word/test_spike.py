"""A saved partial video must never satisfy the online trial's merge gate."""

import importlib.util
from pathlib import Path

import pytest

from backend.games.word_by_word.domain import FIXTURE_TEXT, Clip

spec = importlib.util.spec_from_file_location(
    "word_by_word_spike",
    Path(__file__).resolve().parents[3] / "scripts/games/word-by-word/spike.py",
)
spike = importlib.util.module_from_spec(spec)
spec.loader.exec_module(spike)


@pytest.mark.parametrize(
    ("fail_after_recording", "closed", "expected"),
    [(True, True, False), (False, False, False), (False, True, True)],
)
async def test_trial_requires_completed_generation_and_closure(
    tmp_path, fail_after_recording, closed, expected
):
    class Provider:
        recording = None
        evidence = {}
        close_called = False

        async def run(self, texts, directory, update):
            for index in range(4):
                await update(index, index * 6)
            self.recording = Clip(directory / "story.mp4", 24, 32, 32)
            if fail_after_recording:
                raise RuntimeError("pause_failed")
            return self.recording

        async def close(self):
            self.close_called = True
            return closed

    provider = Provider()
    assert await spike.run_trial(provider, list(FIXTURE_TEXT), tmp_path) is expected
    assert provider.close_called
    assert provider.evidence["generation_completed"] is not fail_after_recording
