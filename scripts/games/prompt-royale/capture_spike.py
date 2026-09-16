"""Run exactly one coordinated Reactor attempt, with independent closure evidence."""

import argparse
import asyncio
import contextlib
import json
import sys
import time
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from backend.games.prompt_royale.config import TOPICS, RoyaleSettings  # noqa: E402
from backend.games.prompt_royale.fast_h3 import FastH3Video  # noqa: E402
from backend.games.prompt_royale.helios import HeliosVideo  # noqa: E402
from backend.games.prompt_royale.media import probe  # noqa: E402
from backend.games.prompt_royale.validation import (  # noqa: E402
    HeliosPromptValidator,
    PromptValidator,
    rendered,
)


async def run(args):
    settings = RoyaleSettings()
    validator = (
        HeliosPromptValidator(settings.prompt_royale_tokenizer)
        if args.model == "helios"
        else PromptValidator()
    )
    prompt, count = validator.validate(
        TOPICS[4], "A penguin wearing a bow tie demonstrates a machine that gently folds clouds."
    )
    run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + uuid4().hex[:8]
    game_root = ROOT / ".local/vibeparty/prompt-royale"
    target = game_root / "spike" / run_id / "clip.mp4"
    target.parent.mkdir(parents=True, exist_ok=True)
    provider = HeliosVideo if args.model == "helios" else FastH3Video
    video = provider(
        settings,
        game_root / "unresolved-provider.json",
        startup_timeout=args.startup_timeout,
        startup_mode=args.startup_mode,
        connection_observer=lambda value: print("SDK status_changed:", value, flush=True),
    )
    evidence = {
        "allocation": args.allocation,
        "attempts": 0,
        "prompt_tokens" if args.model == "helios" else "prompt_characters": count,
        "live_media_passed": False,
    }
    observed_from = time.monotonic()

    async def status(value):
        print("Capture stage:", value)

    async def progress():
        while True:
            elapsed = time.monotonic() - observed_from
            remaining = args.observe_seconds - elapsed if args.observe_seconds else 15
            if remaining <= 0:
                return
            await asyncio.sleep(min(15, remaining))
            current = video.last_evidence
            states = current.get("connection_states", [])
            print(
                "Capture progress:",
                json.dumps(
                    {
                        "elapsed_seconds": round(time.monotonic() - observed_from, 1),
                        "stage": current.get("stage"),
                        "connection": states[-1]["state"] if states else None,
                        "provider_state": current.get("provider_state"),
                        "received_frames": current.get("received_frames", 0),
                        "capture_finished": "elapsed_seconds" in current,
                    }
                ),
                flush=True,
            )

    heartbeat = asyncio.create_task(progress())
    try:
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
        except Exception as error:
            evidence["error_type"] = type(error).__name__
            print("Capture ended:", evidence["error_type"], flush=True)
        if args.observe_seconds:
            # Keep the observation window after an early SDK failure. This is not
            # continued GPU waiting: report the last callback and completed capture.
            await heartbeat
    except BaseException as error:
        evidence["error_type"] = type(error).__name__
    finally:
        heartbeat.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await heartbeat
        evidence.update(video.last_evidence)
        evidence["observation_seconds"] = round(time.monotonic() - observed_from, 3)
        evidence["output_path"] = str(target)
        evidence["all_sessions_confirmed_closed"] = await video.close()
        target.with_suffix(".source.mp4").unlink(missing_ok=True)
        path = target.parent / "evidence.json"
        path.write_text(json.dumps(evidence, indent=2) + "\n")
        path.chmod(0o600)
        print(json.dumps(evidence, indent=2))
    return evidence["live_media_passed"] and evidence["all_sessions_confirmed_closed"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=("fast-h3", "helios"), default="fast-h3")
    parser.add_argument("--allocation", required=True, help="Exclusive allocation from integration")
    parser.add_argument(
        "--startup-timeout",
        type=int,
        help="Allow 1–600 seconds to connect, then 60 seconds to capture (standalone experiment)",
    )
    parser.add_argument("--startup-mode", choices=("sdk", "rest"), default="sdk")
    parser.add_argument(
        "--observe-seconds",
        type=int,
        choices=range(1, 601),
        metavar="1–600",
        default=None,
        help="Continue observing SDK callback state for this long, including after early failure",
    )
    raise SystemExit(0 if asyncio.run(run(parser.parse_args())) else 1)
