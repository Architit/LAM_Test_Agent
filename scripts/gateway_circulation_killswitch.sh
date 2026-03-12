#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ACTION="${1:-status}"

case "$ACTION" in
  on|off|status)
    ;;
  *)
    echo "usage: $0 [on|off|status]"
    exit 2
    ;;
esac

exec "$ROOT/scripts/lam_gateway.sh" circulation-kill-switch "$ACTION"
