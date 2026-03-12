#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BRIDGE_ROOT="${LAM_CAPTAIN_BRIDGE_ROOT:-$ROOT/.gateway/bridge/captain}"
TOKENS_DIR="$BRIDGE_ROOT/mobile_tokens"
PORTAL_ENDPOINT="${LAM_PORTAL_ENDPOINT:-http://127.0.0.1:8765}"

DEVICE_ID="${1:-}"
DEVICE_TYPE="${2:-phone}"
PLATFORM="${3:-android}"
TRANSPORT="${4:-wifi}"
SCOPES="${5:-telemetry_read,device_status,test_reports}"

usage() {
  cat <<'EOF'
Usage:
  scripts/mobile_onboard.sh <device_id> [device_type] [platform] [transport] [scopes_csv]

Example:
  scripts/mobile_onboard.sh device_phone_1 phone android
  scripts/mobile_onboard.sh device_phone_2 phone ios
  scripts/mobile_onboard.sh device_watch_1 watch wearos
  scripts/mobile_onboard.sh device_audio_1 earbuds earbuds
  scripts/mobile_onboard.sh mouse_1 pointer other bluetooth "input_control,device_status"
EOF
}

[[ -n "$DEVICE_ID" ]] || { usage; exit 2; }

mkdir -p "$TOKENS_DIR"
TOKEN="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(24))
PY
)"

NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
FILE="$TOKENS_DIR/${DEVICE_ID}.json"
cat > "$FILE" <<EOF
{
  "device_id": "${DEVICE_ID}",
  "device_type": "${DEVICE_TYPE}",
  "platform": "${PLATFORM}",
  "transport": "${TRANSPORT}",
  "scopes": "${SCOPES}",
  "token": "${TOKEN}",
  "portal_endpoint": "${PORTAL_ENDPOINT}",
  "created_utc": "${NOW}"
}
EOF

echo "[mobile-onboard] token file: $FILE"
echo "[mobile-onboard] register command:"
echo "  scripts/lam_console.sh   # then run:"
echo "  register-device ${DEVICE_ID} ${DEVICE_TYPE} ${PLATFORM} ${PORTAL_ENDPOINT}"
echo "[mobile-onboard] mesh pair command:"
echo "  scripts/device_meshctl.sh pair ${DEVICE_ID} ${DEVICE_TYPE} ${PLATFORM} ${TRANSPORT} ${SCOPES} --endpoint ${PORTAL_ENDPOINT}"
echo "[mobile-onboard] quick links:"
echo "  ${PORTAL_ENDPOINT}/api/status"
echo "  ${PORTAL_ENDPOINT}/api/devices"
