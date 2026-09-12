#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export UV_CACHE_DIR="${UV_CACHE_DIR:-$PWD/.local/uv-cache}"
uv run --frozen --all-extras python -m scripts.run dev &
backend_pid=$!
trap 'kill "$backend_pid" 2>/dev/null || true' EXIT INT TERM
npm --prefix frontend run dev
