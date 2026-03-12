#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
if grep -qiE 'microsoft|wsl' /proc/version 2>/dev/null; then
  export LAM_CONSOLE_FRAME_INTERVAL_SEC="${LAM_CONSOLE_FRAME_INTERVAL_SEC:-0.09}"
  export LAM_CONSOLE_IDLE_FRAME_INTERVAL_SEC="${LAM_CONSOLE_IDLE_FRAME_INTERVAL_SEC:-0.40}"
  export LAM_CONSOLE_INPUT_TIMEOUT_MS="${LAM_CONSOLE_INPUT_TIMEOUT_MS:-80}"
  export LAM_CONSOLE_HEALTH_POLL_SEC="${LAM_CONSOLE_HEALTH_POLL_SEC:-15}"
fi
exec python3 "$ROOT/apps/lam_console/app.py" "$@"
