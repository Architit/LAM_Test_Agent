#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INTERVAL_SEC="${LAM_CIRCULATION_HMAC_ROTATE_INTERVAL_SEC:-86400}"

log() {
  printf '[lam-hmac-rotation-daemon] %s\n' "$*"
}

usage() {
  cat <<'EOF'
Usage:
  scripts/lam_hmac_rotation_daemon.sh --once
  scripts/lam_hmac_rotation_daemon.sh --daemon [--interval-sec N]
  scripts/lam_hmac_rotation_daemon.sh --status
EOF
}

if [[ "${1:-}" == "--status" ]]; then
  "$ROOT/scripts/lam_hmac_rotate.sh" status
  exit 0
fi

if [[ "${1:-}" == "--once" ]]; then
  "$ROOT/scripts/lam_hmac_rotate.sh" rotate
  exit 0
fi

if [[ "${1:-}" == "--daemon" ]]; then
  shift || true
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --interval-sec)
        INTERVAL_SEC="$2"
        shift 2
        ;;
      *)
        echo "unknown arg: $1" >&2
        exit 2
        ;;
    esac
  done
  log "started interval_sec=$INTERVAL_SEC"
  while true; do
    "$ROOT/scripts/lam_hmac_rotate.sh" rotate || true
    sleep "$INTERVAL_SEC"
  done
fi

usage
exit 2

