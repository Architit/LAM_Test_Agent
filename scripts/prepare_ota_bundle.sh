#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${OUT_DIR:-$ROOT/.gateway/ota}"
INPUT_IMAGE="${INPUT_IMAGE:-}"
CHANNEL="${CHANNEL:-stable}"
VERSION="${VERSION:-$(date -u +%Y%m%dT%H%M%SZ)}"

usage() {
  cat <<'EOF'
Usage:
  scripts/prepare_ota_bundle.sh --image /path/to/lam-autonomous-hardened.img [--channel stable|canary] [--version X]

Output:
  .gateway/ota/lam-ota-<channel>-<version>.tar.gz
  .gateway/ota/lam-ota-<channel>-<version>.manifest.json
EOF
}

die() {
  echo "[ota-bundle] $*" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --image) INPUT_IMAGE="$2"; shift 2;;
    --channel) CHANNEL="$2"; shift 2;;
    --version) VERSION="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    *) die "unknown arg: $1";;
  esac
done

[[ -n "$INPUT_IMAGE" ]] || die "--image is required"
[[ -f "$INPUT_IMAGE" ]] || die "image not found: $INPUT_IMAGE"

mkdir -p "$OUT_DIR"

BASENAME="lam-ota-${CHANNEL}-${VERSION}"
TAR_PATH="$OUT_DIR/${BASENAME}.tar.gz"
MANIFEST_PATH="$OUT_DIR/${BASENAME}.manifest.json"

SHA="$(sha256sum "$INPUT_IMAGE" | awk '{print $1}')"
SIZE="$(stat -c '%s' "$INPUT_IMAGE")"

cat > "$MANIFEST_PATH" <<EOF
{
  "bundle": "${BASENAME}",
  "channel": "${CHANNEL}",
  "version": "${VERSION}",
  "image_file": "$(basename "$INPUT_IMAGE")",
  "sha256": "${SHA}",
  "size_bytes": ${SIZE},
  "rollback_required_partition": "recovery",
  "created_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

tar -czf "$TAR_PATH" -C "$(dirname "$INPUT_IMAGE")" "$(basename "$INPUT_IMAGE")" -C "$OUT_DIR" "$(basename "$MANIFEST_PATH")"

echo "[ota-bundle] bundle: $TAR_PATH"
echo "[ota-bundle] manifest: $MANIFEST_PATH"

