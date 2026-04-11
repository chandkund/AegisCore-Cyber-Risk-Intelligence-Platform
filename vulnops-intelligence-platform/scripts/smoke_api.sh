#!/usr/bin/env bash
# Black-box API smoke: GET /health (always) and optionally GET /ready (needs PostgreSQL).
# Usage:
#   API_BASE_URL=http://localhost:8000 ./scripts/smoke_api.sh
#   SKIP_READY=1 ./scripts/smoke_api.sh   # only /health
set -euo pipefail
BASE="${API_BASE_URL:-http://127.0.0.1:8000}"
echo "Smoke: GET ${BASE}/health"
curl -sfS "${BASE}/health" >/dev/null
if [[ "${SKIP_READY:-}" == "1" ]]; then
  echo "SKIP_READY=1 — skipping GET /ready"
  echo "OK (health only)"
  exit 0
fi
echo "Smoke: GET ${BASE}/ready"
curl -sfS "${BASE}/ready" >/dev/null
echo "OK (health + ready)"
