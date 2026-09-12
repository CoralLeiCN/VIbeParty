"""Install only the pinned UMT5 tokenizer, never model weights."""

import argparse
import hashlib
import os
import urllib.request
from pathlib import Path

REVISION = "66cb9e7e85526fe440a945569e42c72fb6cbc0ad"
SHA256 = "af904105ce1071b1202bba0059a841f4a7b85b48b6ec179c4948e3483476e0dd"
root = Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser()
parser.add_argument("--destination", type=Path)
args = parser.parse_args()
configured = os.environ.get("PROMPT_ROYALE_TOKENIZER")
if not configured and (root / ".env").is_file():
    for line in (root / ".env").read_text().splitlines():
        if line.startswith("PROMPT_ROYALE_TOKENIZER="):
            configured = line.split("=", 1)[1].strip().strip('"').strip("'")
target = args.destination or Path(
    configured or ".local/vibeparty/prompt-royale/tokenizer/tokenizer.json"
)
if not target.is_absolute():
    target = root / target
if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == SHA256:
    print("Pinned tokenizer already verified.")
else:
    with urllib.request.urlopen(
        f"https://huggingface.co/google/umt5-xxl/resolve/{REVISION}/tokenizer.json", timeout=30
    ) as response:
        data = response.read(20 * 1024 * 1024)
    if hashlib.sha256(data).hexdigest() != SHA256:
        raise SystemExit("Tokenizer checksum mismatch; asset not installed.")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    print("Pinned tokenizer downloaded and verified.")
