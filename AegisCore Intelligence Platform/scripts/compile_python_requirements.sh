#!/usr/bin/env bash
# Regenerate committed pip-compile outputs from backend/requirements/*.in
# Run from repository root on Python 3.12 (see .python-version).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"
python -m pip install -q "pip-tools>=7,<8"
python -m piptools compile requirements/base.in -o requirements/base.txt --resolver=backtracking
python -m piptools compile requirements/dev.in -o requirements/dev.txt --resolver=backtracking
echo "Updated backend/requirements/base.txt and dev.txt — review diff and commit."
