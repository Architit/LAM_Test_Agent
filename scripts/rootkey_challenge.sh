#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HUB_ROOT="${LAM_HUB_ROOT:-$ROOT/.gateway/hub}"
MEDIA_ROOT="${LAM_ROOTKEY_MEDIA_ROOT:-$ROOT/.gateway/exchange/removable}"
KEY_REL="${LAM_ROOTKEY_FILE_REL:-.radriloniuma/rootkey/architit_root.key}"
RESP_REL="${LAM_ROOTKEY_RESPONSE_FILE_REL:-.radriloniuma/rootkey/challenge_response.sha256}"
CHALLENGE_FILE="$HUB_ROOT/rootkey_challenge.json"
TTL_SEC="${LAM_ROOTKEY_CHALLENGE_TTL_SEC:-180}"

mkdir -p "$HUB_ROOT"

usage() {
  cat <<'EOF'
Usage:
  scripts/rootkey_challenge.sh issue [--ttl-sec 180]
  scripts/rootkey_challenge.sh solve
  scripts/rootkey_challenge.sh status
  scripts/rootkey_challenge.sh clear
EOF
}

cmd="${1:-status}"
shift || true

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ttl-sec) TTL_SEC="$2"; shift 2;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done

case "$cmd" in
  issue)
    nonce="$(head -c 16 /dev/urandom | od -An -tx1 | tr -d ' \n')"
    cat > "$CHALLENGE_FILE" <<EOF
{
  "nonce": "$nonce",
  "issued_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "ttl_sec": $TTL_SEC,
  "used": false
}
EOF
    echo "issued nonce=$nonce ttl_sec=$TTL_SEC"
    ;;
  solve)
    [[ -f "$CHALLENGE_FILE" ]] || { echo "challenge missing: $CHALLENGE_FILE" >&2; exit 1; }
    key_file="$MEDIA_ROOT/$KEY_REL"
    [[ -f "$key_file" ]] || { echo "key file missing: $key_file" >&2; exit 1; }
    nonce="$(python3 - "$CHALLENGE_FILE" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1])
obj=json.loads(p.read_text())
print(str(obj.get("nonce","")).strip())
PY
)"
    [[ -n "$nonce" ]] || { echo "invalid challenge nonce" >&2; exit 1; }
    key_digest="$(sha256sum "$key_file" | awk '{print $1}')"
    response="$(printf '%s:%s' "$nonce" "$key_digest" | sha256sum | awk '{print $1}')"
    resp_file="$MEDIA_ROOT/$RESP_REL"
    mkdir -p "$(dirname "$resp_file")"
    printf '%s\n' "$response" > "$resp_file"
    echo "response_written=$resp_file"
    ;;
  status)
    [[ -f "$CHALLENGE_FILE" ]] && cat "$CHALLENGE_FILE" || echo '{"challenge":"absent"}'
    ;;
  clear)
    rm -f "$CHALLENGE_FILE" "$MEDIA_ROOT/$RESP_REL"
    echo "cleared"
    ;;
  *)
    usage
    exit 2
    ;;
esac
