#!/usr/bin/env bash
set -euo pipefail

# Minimal recovery-mode switch helper.
# This script does not rewrite bootloader config blindly; it prepares
# recovery marker and asks systemctl to reboot into firmware or normal mode.

MARKER_DIR="${MARKER_DIR:-/recovery/lam_rollback}"
MARKER_FILE="${MARKER_FILE:-$MARKER_DIR/recovery_request.json}"
MODE="${1:-status}"

usage() {
  cat <<'EOF'
Usage:
  sudo scripts/recovery_switch.sh status
  sudo scripts/recovery_switch.sh request
  sudo scripts/recovery_switch.sh clear
  sudo scripts/recovery_switch.sh reboot
EOF
}

require_root() {
  [[ "${EUID}" -eq 0 ]] || { echo "[recovery-switch] run as root" >&2; exit 1; }
}

status() {
  if [[ -f "$MARKER_FILE" ]]; then
    echo "[recovery-switch] pending marker: $MARKER_FILE"
    cat "$MARKER_FILE"
  else
    echo "[recovery-switch] no recovery marker"
  fi
}

request() {
  require_root
  mkdir -p "$MARKER_DIR"
  cat > "$MARKER_FILE" <<EOF
{
  "requested_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "reason": "operator_manual_recovery_request"
}
EOF
  echo "[recovery-switch] marker created: $MARKER_FILE"
}

clear() {
  require_root
  rm -f "$MARKER_FILE"
  echo "[recovery-switch] marker cleared"
}

reboot_now() {
  require_root
  if [[ -f "$MARKER_FILE" ]]; then
    echo "[recovery-switch] rebooting with recovery marker present"
  else
    echo "[recovery-switch] rebooting without recovery marker"
  fi
  systemctl reboot
}

case "$MODE" in
  status) status;;
  request) request;;
  clear) clear;;
  reboot) reboot_now;;
  -h|--help) usage;;
  *) usage; exit 2;;
esac

