#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f .env ]]; then
  echo "[ERROR] .env not found in $ROOT_DIR"
  echo "Please copy .env.example to .env and fill values."
  exit 1
fi

set -a
source .env
set +a

exec uvicorn omnicore_api:app --host 0.0.0.0 --port 8000
