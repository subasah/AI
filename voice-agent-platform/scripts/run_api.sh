#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="$ROOT"
export RELOAD="${RELOAD:-false}"
cd "$ROOT"
exec python3 -m uvicorn backend.app.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8080}" --reload
