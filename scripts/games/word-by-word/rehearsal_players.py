"""API-only extra players for a labelled local fixture browser rehearsal.

This does not constitute physical-phone or live-provider evidence. The first player
and host use the browser; this helper supplies the other independent cookie jars.
"""

import argparse
import json
import os
from pathlib import Path

import httpx

COOKIE = "vp_word_by_word"
API = "/api/games/word-by-word"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--origin", default="http://localhost:5174")
    parser.add_argument("--sessions", type=Path, default=Path("/tmp/word-by-word-players.json"))
    parser.add_argument("--join", metavar="CODE")
    parser.add_argument("--names", nargs="+", default=["Bo", "Cy"])
    parser.add_argument("--submit", action="store_true")
    args = parser.parse_args()
    players = json.loads(args.sessions.read_text()) if args.sessions.exists() else []
    if args.join:
        for name in args.names:
            with httpx.Client(
                base_url=args.origin, headers={"Origin": args.origin}, trust_env=False
            ) as client:
                response = client.post(API + "/join", json={"code": args.join, "name": name})
                response.raise_for_status()
                players.append({"name": name, "cookie": client.cookies.get(COOKIE)})
                print(f"Joined fixture API player: {name}")
        fd = os.open(args.sessions, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as output:
            json.dump(players, output)
    if args.submit:
        for player in players:
            with httpx.Client(
                base_url=args.origin,
                headers={"Origin": args.origin},
                cookies={COOKIE: player["cookie"]},
                trust_env=False,
            ) as client:
                response = client.get(API + "/state")
                if response.status_code == 401:
                    continue
                response.raise_for_status()
                state = response.json()
                if state["mode"] != "fixture" or state["phase"] != "INPUT":
                    raise SystemExit("This helper only submits during fixture collection.")
                for assignment in state["assignments"]:
                    response = client.post(
                        API + "/contribution",
                        json={
                            "round_id": state["round_id"],
                            "slot_index": assignment["index"],
                            "text": assignment["fixture_text"],
                        },
                    )
                    response.raise_for_status()
                    print(f"Accepted fixture API contribution from {player['name']}")


if __name__ == "__main__":
    main()
