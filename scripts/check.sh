#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export UV_CACHE_DIR="${UV_CACHE_DIR:-$PWD/.local/uv-cache}"
uv run --frozen --all-extras ruff check backend scripts/run.py scripts/prepare_assets.py scripts/rehearsal_room_codes.py
uv run --frozen --all-extras ruff format --check backend scripts/run.py scripts/prepare_assets.py scripts/rehearsal_room_codes.py
npm --prefix frontend run lint
npm --prefix frontend run build
uv run --frozen --all-extras pytest
