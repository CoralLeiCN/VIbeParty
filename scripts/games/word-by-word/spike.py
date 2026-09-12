"""One explicitly coordinated FastH3 trial; never run alongside another live slot.

Run as a script from the repository root. Only public demo text is built in.
A new process does not authorize another paid attempt: use integration's ledger.
"""

import argparse
import asyncio
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from backend.games.word_by_word.domain import FIXTURE_TEXT, validate_text  # noqa: E402
from backend.games.word_by_word.live import CaptureError, FastH3Provider, LiveSettings  # noqa: E402


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--slot", required=True, help="Integration's allocated trial identifier")
    readiness = parser.add_mutually_exclusive_group(required=True)
    readiness.add_argument("--previous-session-closed", action="store_true")
    readiness.add_argument(
        "--account-precheck-waived",
        action="store_true",
        help="Only with the user's explicit direction to proceed without account prechecks",
    )
    parser.add_argument("--contributions-json", type=Path, help="JSON array of four accepted texts")
    args = parser.parse_args()
    for executable in ("ffmpeg", "ffprobe"):
        if not shutil.which(executable):
            raise SystemExit(f"{executable} is required; no provider request made")
    settings = LiveSettings(_env_file=args.env_file)
    key = settings.reactor_api_key.get_secret_value()
    if not key.startswith("rk_"):
        raise SystemExit("Configure a Reactor API key; no provider request made")
    if not args.slot.strip():
        raise SystemExit("A coordinated slot is required; no provider request made")
    texts = (
        json.loads(args.contributions_json.read_text())
        if args.contributions_json
        else list(FIXTURE_TEXT)
    )
    if not isinstance(texts, list) or len(texts) != 4 or not all(isinstance(t, str) for t in texts):
        raise SystemExit("Supply exactly four strings; no provider request made")
    texts = [validate_text(t) for t in texts]
    out = Path(args.output)
    # Never overwrite a prior trial or its closure evidence.
    out.mkdir(parents=True, mode=0o700, exist_ok=False)
    provider = FastH3Provider(key, evidence_path=out / "evidence.json")
    provider.evidence["slot"] = args.slot
    provider.evidence["started_utc"] = datetime.now(UTC).isoformat()
    provider.evidence["session_attempts"] = 1
    provider.evidence["account_precheck"] = (
        "waived_by_user" if args.account_precheck_waived else "previous_session_closed_confirmed"
    )
    provider.evidence["contribution_codepoints"] = [len(t) for t in texts]
    provider.evidence["continuity_review"] = "required"
    provider.evidence["account_spend"] = "operator measurement required"
    try:
        async with asyncio.timeout(120):
            await provider.open()
            for index in range(4):
                async with asyncio.timeout(30):
                    clip = await provider.segment(texts, index, out / f"{index}.mp4")
                print(json.dumps({"saved_clip": index, "duration": clip.duration}), flush=True)
    except (Exception, asyncio.CancelledError) as error:
        provider.evidence["error_type"] = type(error).__name__
        if isinstance(error, CaptureError):
            # CaptureError messages are local fixed codes, never raw provider errors.
            provider.evidence["error_code"] = str(error)
        print(json.dumps({"trial_failed": type(error).__name__}), flush=True)
    finally:
        try:
            confirmed = await asyncio.wait_for(provider.close(), 20)
        except (Exception, asyncio.CancelledError):
            confirmed = False
        print(
            json.dumps({"closure_confirmed": confirmed, "evidence": str(out / "evidence.json")}),
            flush=True,
        )
    if not confirmed or len(provider.evidence["clips"]) != 4:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
