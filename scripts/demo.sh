#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export UV_CACHE_DIR="${UV_CACHE_DIR:-$PWD/.local/uv-cache}"
npm --prefix frontend run build
exec uv run --frozen --all-extras python -m scripts.run demo
