"""Run only in the exclusive live slot granted by the integration session."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from backend.games.reverse_prompt.config import GameSettings
from backend.games.reverse_prompt.quota import Quota
from backend.games.reverse_prompt.reactor_video import FastH3Provider
from backend.shared.config import Settings

parser = argparse.ArgumentParser()
parser.add_argument("--slot", required=True, help="Coordinator's exclusive slot reference")
parser.add_argument("--force-timeout", action="store_true")
args = parser.parse_args()


async def run():
    settings = Settings()
    config = GameSettings()
    if not config.reverse_prompt_live_enabled or not config.reactor_api_key.get_secret_value():
        raise SystemExit("Live mode/key not configured; request the integration slot first.")
    quota = Quota(settings.reverse_prompt_quota_file)
    provider = FastH3Provider(config.reactor_api_key.get_secret_value(), quota)
    directory = settings.media_dir("reverse-prompt") / "spike"
    try:
        async with asyncio.timeout(2 if args.force_timeout else 105):
            await provider.generate("A red balloon floats past a blue tower.", directory, 0)
    except Exception as error:
        print(json.dumps({"result": "failed", "category": type(error).__name__}))
    finally:
        try:
            await provider.close()
        except Exception as error:
            print(json.dumps({"cleanup": "unresolved", "category": type(error).__name__}))
        print(
            json.dumps(
                {
                    "slot": args.slot,
                    "evidence": provider.last_evidence,
                    "remaining": quota.read()["remaining"],
                    "unresolved": quota.read()["unresolved"],
                }
            )
        )


asyncio.run(run())
