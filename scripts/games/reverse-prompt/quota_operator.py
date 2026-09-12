"""Manual campaign allocation/reconciliation; never invoked by gameplay."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from backend.games.reverse_prompt.quota import Quota

parser = argparse.ArgumentParser()
parser.add_argument("path", type=Path)
parser.add_argument("action", choices=["inspect", "initialize", "confirm-closed"])
parser.add_argument("--attempt")
parser.add_argument("--evidence", help="Operator's independent provider closure check")
args = parser.parse_args()
quota = Quota(args.path)
if args.action == "initialize":
    quota.initialize()
elif args.action == "confirm-closed":
    if not args.attempt or not args.evidence:
        parser.error("An exact attempt and independent closure evidence are required")
    quota.confirm_closed(args.attempt, "operator: " + args.evidence)
value = quota.read()
print(
    {
        "remaining": value["remaining"],
        "unresolved": value["unresolved"],
        "latest_attempt": value["attempts"][-1] if value["attempts"] else None,
    }
)
