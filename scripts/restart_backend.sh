#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

PID="$(lsof -tiTCP:8000 -sTCP:LISTEN || true)"
if [[ -n "$PID" ]]; then
  kill "$PID" || true
  sleep 1
fi

"$ROOT_DIR/scripts/start_backend.sh"
