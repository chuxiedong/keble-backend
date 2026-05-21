#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -d ".venv" ]; then
  echo ".venv not found. Run scripts/dev_bootstrap.sh first."
  exit 1
fi

source .venv/bin/activate
python scripts/build_route_manifest.py
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

