"""One coordinated topic API call; reports timeout and allowance evidence without secrets."""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from backend.games.prompt_royale.config import RoyaleSettings  # noqa: E402
from backend.games.prompt_royale.providers import TOPIC_MODEL, Topics  # noqa: E402


async def run(allocation):
    provider = Topics(RoyaleSettings(prompt_royale_topic_mode="live", prompt_royale_topic_calls=1))
    evidence = {
        "allocation": allocation,
        "model": TOPIC_MODEL,
        "timeout_seconds": 10,
        "max_output_tokens": 64,
        "allowance": 1,
        "passed": False,
    }
    started = time.monotonic()
    try:
        evidence["topic"] = await provider.suggest()
        evidence["passed"] = True
    except Exception as error:
        evidence["error_type"] = type(error).__name__
    evidence.update(calls=provider.calls, elapsed_seconds=round(time.monotonic() - started, 3))
    target = ROOT / ".local/vibeparty/prompt-royale/spike/topic-evidence.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))
    return evidence["passed"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--allocation", required=True)
    raise SystemExit(0 if asyncio.run(run(parser.parse_args().allocation)) else 1)
