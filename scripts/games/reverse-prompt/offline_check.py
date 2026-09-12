"""Run with every socket connection blocked, including model load/warmup."""

import argparse
import json
import socket
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from backend.games.reverse_prompt.scoring import LocalScorer

parser = argparse.ArgumentParser()
parser.add_argument("path", type=Path)
args = parser.parse_args()


def blocked(*args, **kwargs):
    raise AssertionError("Scoring attempted network access")


socket.socket.connect = blocked
socket.create_connection = blocked
model = LocalScorer()
model.load(args.path)
original = "A tiny astronaut pours tea for a giant frog."
guesses = [original, "A little space explorer serves tea to an enormous frog."]
start = time.monotonic()
scores = model.score(original, guesses)
assert scores[0] == 100
assert model.score(original, [original, original]) == [100, 100]
try:
    model.validate("!" * 300)
except ValueError:
    pass
else:
    raise AssertionError("Over-token input accepted")
print(
    json.dumps(
        {
            "offline": True,
            "scores": scores,
            "token_limit": model.token_limit,
            "batch_seconds": round(time.monotonic() - start, 4),
        }
    )
)
