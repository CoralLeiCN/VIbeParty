"""Explicit setup download. The running app never downloads a model."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from backend.games.reverse_prompt.scoring import MODEL_ID, MODEL_REVISION

parser = argparse.ArgumentParser()
parser.add_argument("path", type=Path)
parser.add_argument("--existing", action="store_true", help="Verify already downloaded files")
args = parser.parse_args()
if not args.existing:
    from huggingface_hub import snapshot_download

    snapshot_download(
        MODEL_ID,
        revision=MODEL_REVISION,
        local_dir=args.path,
        allow_patterns=["*.json", "*.safetensors", "vocab.txt", "1_Pooling/*"],
    )
files = [
    p
    for p in args.path.rglob("*")
    if p.is_file() and ".cache" not in p.parts and p.name != "vibeparty-model.json"
]
manifest = {
    "model": MODEL_ID,
    "revision": MODEL_REVISION,
    "sha256": {
        str(p.relative_to(args.path)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files
    },
}
(args.path / "vibeparty-model.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("Pinned model manifest written; run offline_check.py before live play.")
