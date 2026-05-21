#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"

if [ ! -d ".venv" ]; then
  "$PYTHON_BIN" -m venv .venv
fi

source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python scripts/build_route_manifest.py

echo "Bootstrap complete."
echo "Run: source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

