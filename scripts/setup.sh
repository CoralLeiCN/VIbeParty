#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
bash scripts/setup-worktree.sh
export UV_CACHE_DIR="${UV_CACHE_DIR:-$PWD/.local/uv-cache}"
uv sync --frozen --all-extras
npm --prefix frontend ci
uv run --frozen --all-extras python -m scripts.prepare_assets
