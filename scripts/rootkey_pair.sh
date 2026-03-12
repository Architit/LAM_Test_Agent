#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HUB_ROOT="${LAM_HUB_ROOT:-$ROOT/.gateway/hub}"
MEDIA_ROOT="${LAM_ROOTKEY_MEDIA_ROOT:-$ROOT/.gateway/exchange/removable}"
KEY_REL="${LAM_ROOTKEY_FILE_REL:-.radriloniuma/rootkey/architit_root.key}"
PAIR_FILE="$HUB_ROOT/rootkey_pairing.json"
SHA_FILE="$HUB_ROOT/rootkey_expected_sha256.txt"

mkdir -p "$HUB_ROOT"

usage() {
  cat <<'EOF'
Usage:
  scripts/rootkey_pair.sh pair [--owner architit] [--key-id AK-001]
  scripts/rootkey_pair.sh revoke
  scripts/rootkey_pair.sh status
EOF
}

cmd="${1:-status}"
shift || true

owner="architit"
key_id="AK-001"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --owner) owner="$2"; shift 2;;
    --key-id) key_id="$2"; shift 2;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done

case "$cmd" in
  pair)
    key_file="$MEDIA_ROOT/$KEY_REL"
    [[ -f "$key_file" ]] || { echo "rootkey file not found: $key_file" >&2; exit 1; }
    digest="$(sha256sum "$key_file" | awk '{print $1}')"
    cat > "$PAIR_FILE" <<EOF
{
  "enabled": true,
  "owner": "$owner",
  "key_id": "$key_id",
  "paired_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "media_root": "$MEDIA_ROOT",
  "key_file_rel": "$KEY_REL"
}
EOF
    printf "%s\n" "$digest" > "$SHA_FILE"
    echo "paired owner=$owner key_id=$key_id sha256=$digest"
    ;;
  revoke)
    cat > "$PAIR_FILE" <<EOF
{
  "enabled": false,
  "owner": "$owner",
  "key_id": "$key_id",
  "revoked_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
    rm -f "$SHA_FILE"
    echo "revoked"
    ;;
  status)
    [[ -f "$PAIR_FILE" ]] && cat "$PAIR_FILE" || echo '{"enabled":false}'
    [[ -f "$SHA_FILE" ]] && echo "expected_sha256=$(cat "$SHA_FILE")" || true
    ;;
  *)
    usage
    exit 2
    ;;
esac
