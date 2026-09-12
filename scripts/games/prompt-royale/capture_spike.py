"""Run exactly one coordinated Helios attempt, with independent closure evidence."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from backend.games.prompt_royale.config import TOPICS, RoyaleSettings  # noqa: E402
from backend.games.prompt_royale.helios import HeliosVideo  # noqa: E402
from backend.games.prompt_royale.media import probe  # noqa: E402
from backend.games.prompt_royale.validation import PromptValidator, rendered  # noqa: E402


async def run(args):
    settings = RoyaleSettings()
    prompt, count = PromptValidator(settings.prompt_royale_tokenizer).validate(
        TOPICS[4], "A penguin wearing a bow tie demonstrates a machine that gently folds clouds."
    )
    target = ROOT / ".local/vibeparty/prompt-royale/spike/clip.mp4"
    target.parent.mkdir(parents=True, exist_ok=True)
    video = HeliosVideo(settings, target.parent.parent / "unresolved-provider.json")
    evidence = {
        "allocation": args.allocation,
        "attempts": 0,
        "tokens": count,
        "live_media_passed": False,
    }

    async def status(value):
        print("Capture stage:", value)

    try:
        if not settings.reactor_api_key:
            raise ValueError("Reactor key missing")
        if video.uncertain:
            raise ValueError("Previous spike has unresolved provider state")
        evidence["attempts"] = 1
        await video.generate(rendered(TOPICS[4], prompt), 42, target, 0, status)
        info = await probe(target, settings.prompt_royale_ffprobe)
        evidence.update(
            duration=info["format"]["duration"],
            streams=[
                {key: stream.get(key) for key in ["codec_name", "width", "height", "pix_fmt"]}
                for stream in info["streams"]
            ],
            live_media_passed=True,
        )
    except BaseException as error:
        evidence["error_type"] = type(error).__name__
    finally:
        evidence.update(video.last_evidence)
        evidence["all_sessions_confirmed_closed"] = await video.close()
        target.with_suffix(".source.mp4").unlink(missing_ok=True)
        path = target.parent / "evidence.json"
        path.write_text(json.dumps(evidence, indent=2) + "\n")
        print(json.dumps(evidence, indent=2))
    return evidence["live_media_passed"] and evidence["all_sessions_confirmed_closed"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--allocation", required=True, help="Exclusive allocation from integration")
    raise SystemExit(0 if asyncio.run(run(parser.parse_args())) else 1)
