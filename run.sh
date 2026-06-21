#!/usr/bin/env bash
# Cron entry point for the weekly digest.
# Sources secrets, then runs the pipeline via uv (which provisions the
# dependency environment automatically from pyproject.toml).
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

if [[ ! -f "$DIR/mysecrets" ]]; then
  echo "missing $DIR/mysecrets (copy mysecrets.example and fill it in)" >&2
  exit 1
fi
# shellcheck disable=SC1091
source "$DIR/mysecrets"

# uv lives in /opt/homebrew/bin or ~/.local/bin; make sure cron can find it.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

exec uv run --quiet python -m weekly_digest "$@"
