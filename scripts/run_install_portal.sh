#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${1:-8099}"
HOST="${2:-0.0.0.0}"
LAN_IP="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"

cd "$ROOT/apps/install_portal"
echo "[install-portal] local: http://127.0.0.1:${PORT}"
if [[ -n "${LAN_IP}" ]]; then
  echo "[install-portal] lan:   http://${LAN_IP}:${PORT}"
fi
exec python3 -m http.server "$PORT" --bind "$HOST"
