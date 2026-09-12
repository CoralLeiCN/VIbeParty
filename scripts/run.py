"""One local process; no reload and no workers sharing in-memory rooms."""

import argparse
import os

import uvicorn

from backend.shared.config import Settings

parser = argparse.ArgumentParser()
parser.add_argument("mode", choices=["dev", "demo"], default="demo", nargs="?")
args = parser.parse_args()
settings = Settings()
if args.mode == "dev":
    os.environ["BROWSER_ORIGIN"] = os.environ.get(
        "BROWSER_ORIGIN", f"http://localhost:{settings.frontend_port}"
    )
uvicorn.run("backend.app:app", host="0.0.0.0", port=settings.backend_port, workers=1)
