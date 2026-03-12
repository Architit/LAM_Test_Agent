#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PRIMARY_FILE="${LAM_CIRCULATION_HMAC_KEY_FILE:-$ROOT/.gateway/security/circulation_hmac.key}"
SECONDARY_FILE="${LAM_CIRCULATION_HMAC_SECONDARY_KEY_FILE:-$ROOT/.gateway/security/circulation_hmac_prev.key}"
ROTATION_STATE_FILE="${LAM_CIRCULATION_HMAC_ROTATION_STATE_FILE:-$ROOT/.gateway/security/circulation_hmac_rotation.json}"
GRACE_SEC="${LAM_CIRCULATION_HMAC_SECONDARY_GRACE_SEC:-86400}"
KEY_BYTES="${LAM_CIRCULATION_HMAC_KEY_BYTES:-32}"

log() {
  printf '[lam-hmac-rotate] %s\n' "$*"
}

generate_key() {
  openssl rand -hex "$KEY_BYTES"
}

rotate_once() {
  local now valid_until new_key
  mkdir -p "$(dirname "$PRIMARY_FILE")" "$(dirname "$SECONDARY_FILE")"
  if [[ -f "$PRIMARY_FILE" ]]; then
    cp -f "$PRIMARY_FILE" "$SECONDARY_FILE"
    chmod 600 "$SECONDARY_FILE" || true
  fi
  new_key="$(generate_key)"
  printf '%s\n' "$new_key" > "$PRIMARY_FILE"
  chmod 600 "$PRIMARY_FILE" || true
  now="$(date +%s)"
  valid_until="$((now + GRACE_SEC))"
  cat > "$ROTATION_STATE_FILE" <<EOF
{
  "schema": "lam.circulation.hmac.rotation.v1",
  "rotated_at_epoch": $now,
  "secondary_valid_until_epoch": $valid_until,
  "primary_key_file": "$PRIMARY_FILE",
  "secondary_key_file": "$SECONDARY_FILE",
  "grace_sec": $GRACE_SEC
}
EOF
  log "rotated primary key; grace until epoch=$valid_until"
}

status() {
  printf "primary_file=%s\n" "$PRIMARY_FILE"
  printf "secondary_file=%s\n" "$SECONDARY_FILE"
  printf "rotation_state_file=%s\n" "$ROTATION_STATE_FILE"
  [[ -f "$PRIMARY_FILE" ]] && printf "primary_exists=1\n" || printf "primary_exists=0\n"
  [[ -f "$SECONDARY_FILE" ]] && printf "secondary_exists=1\n" || printf "secondary_exists=0\n"
  if [[ -f "$ROTATION_STATE_FILE" ]]; then
    printf "rotation_state=%s\n" "$(tr -d '\n' < "$ROTATION_STATE_FILE")"
  fi
}

clear_secondary() {
  rm -f "$SECONDARY_FILE"
  if [[ -f "$ROTATION_STATE_FILE" ]]; then
    python3 - "$ROTATION_STATE_FILE" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
obj = {}
try:
    obj = json.loads(p.read_text(encoding="utf-8"))
except Exception:
    pass
obj["secondary_valid_until_epoch"] = 0
p.write_text(json.dumps(obj, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
PY
  fi
  log "secondary key cleared"
}

usage() {
  cat <<'EOF'
Usage:
  scripts/lam_hmac_rotate.sh rotate
  scripts/lam_hmac_rotate.sh status
  scripts/lam_hmac_rotate.sh clear-secondary
EOF
}

case "${1:-}" in
  rotate) rotate_once ;;
  status) status ;;
  clear-secondary) clear_secondary ;;
  *) usage; exit 2 ;;
esac

