#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt || true

echo "✅ Virtual env ready. Activate with: source .venv/bin/activate"
