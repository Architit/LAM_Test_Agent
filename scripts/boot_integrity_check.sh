#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_ROOT="${LAM_STATE_ROOT:-$ROOT/.gateway}"
OUT_DIR="${LAM_BOOT_STATE_DIR:-$STATE_ROOT/security}"
OUT_FILE="$OUT_DIR/boot_integrity_state.json"

REQUIRE_UEFI="${LAM_BOOT_REQUIRE_UEFI:-1}"
REQUIRE_SECURE_BOOT="${LAM_BOOT_REQUIRE_SECURE_BOOT:-0}"

mkdir -p "$OUT_DIR"

ok=1
reason="ok"
uefi_present=0
secure_boot_enabled=0

if [[ -d /sys/firmware/efi ]]; then
  uefi_present=1
fi

if [[ "$REQUIRE_UEFI" == "1" && "$uefi_present" != "1" ]]; then
  ok=0
  reason="uefi_missing"
fi

if [[ "$uefi_present" == "1" ]]; then
  sb_file="$(ls /sys/firmware/efi/efivars/SecureBoot-* 2>/dev/null | head -n1 || true)"
  if [[ -n "$sb_file" ]]; then
    sb_val="$(od -An -t u1 -j4 -N1 "$sb_file" 2>/dev/null | tr -d '[:space:]' || true)"
    if [[ "$sb_val" == "1" ]]; then
      secure_boot_enabled=1
    fi
  fi
fi

if [[ "$REQUIRE_SECURE_BOOT" == "1" && "$secure_boot_enabled" != "1" ]]; then
  ok=0
  reason="secure_boot_required"
fi

ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
cat > "$OUT_FILE" <<EOF
{
  "ts_utc": "$ts",
  "ok": $([[ "$ok" == "1" ]] && echo true || echo false),
  "reason": "$reason",
  "require_uefi": $([[ "$REQUIRE_UEFI" == "1" ]] && echo true || echo false),
  "require_secure_boot": $([[ "$REQUIRE_SECURE_BOOT" == "1" ]] && echo true || echo false),
  "uefi_present": $([[ "$uefi_present" == "1" ]] && echo true || echo false),
  "secure_boot_enabled": $([[ "$secure_boot_enabled" == "1" ]] && echo true || echo false)
}
EOF

cat "$OUT_FILE"

if [[ "$ok" != "1" ]]; then
  exit 1
fi
