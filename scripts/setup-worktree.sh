#!/usr/bin/env bash
set -euo pipefail

# Never source or print .env: it contains backend credentials.
umask 077
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(git -C "$script_dir/.." rev-parse --show-toplevel)"
destination="$project_root/.env"

if ! git -C "$project_root" check-ignore -q -- .env; then
  printf 'Setup stopped: the root .env must be ignored by Git.\n' >&2
  exit 1
fi

if [[ -L "$destination" || ( -e "$destination" && ! -f "$destination" ) ]]; then
  printf 'Setup stopped: .env must be a regular file, not a symlink or directory.\n' >&2
  exit 1
fi

if [[ -f "$destination" ]]; then
  chmod 600 "$destination"
  printf 'Kept the existing .env. Environment setup is complete.\n'
  exit 0
fi

if [[ -n "${VIBEPARTY_ENV_SOURCE:-}" ]]; then
  source_env="$VIBEPARTY_ENV_SOURCE"
else
  # Git lists the original checkout first. NUL records preserve spaces in paths.
  IFS= read -r -d '' first_worktree < <(git -C "$project_root" worktree list --porcelain -z)
  primary_root="${first_worktree#worktree }"
  source_env="$primary_root/.env"
fi

if [[ -L "$source_env" || ( -e "$source_env" && ! -f "$source_env" ) ]]; then
  printf 'Setup stopped: the source .env must be a regular file.\n' >&2
  exit 1
fi

if [[ -f "$source_env" ]]; then
  cp -n "$source_env" "$destination"
  chmod 600 "$destination"
  printf 'Copied the private .env into this worktree. Environment setup is complete.\n'
elif [[ -n "${VIBEPARTY_ENV_SOURCE:-}" ]]; then
  printf 'Setup stopped: VIBEPARTY_ENV_SOURCE does not point to an existing file.\n' >&2
  exit 1
else
  cp -n "$project_root/example.env" "$destination"
  chmod 600 "$destination"
  printf 'No source .env found; created .env from example.env in fixture mode.\n'
  printf 'Set REACTOR_API_KEY in the original checkout .env before using live generation.\n'
fi
