#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NODE_ID="${LAM_NODE_ID:-$(hostname -s 2>/dev/null || hostname)}"
STATE_ROOT="${LAM_CIRCULATION_STATE_ROOT:-$ROOT/.gateway/circulation}"
INVERSION_ROOT="$STATE_ROOT/inversion"
OUTBOX_ROOT="$INVERSION_ROOT/outbox/$NODE_ID"
INBOX_ROOT="$INVERSION_ROOT/inbox"
SEEN_FILE="$INVERSION_ROOT/seen_sha256.tsv"
INDEX_FILE="$INVERSION_ROOT/index.jsonl"
REPORT_LIMIT="${LAM_CIRCULATION_REPORT_LIMIT:-12}"
ERROR_LINES="${LAM_CIRCULATION_ERROR_LINES:-80}"
INTERVAL_SEC="${LAM_CIRCULATION_INTERVAL_SEC:-12}"
CRYPTO_REQUIRED="${LAM_CIRCULATION_REQUIRE_CRYPTO_MIRROR:-1}"
HMAC_KEY_ENV="${LAM_CIRCULATION_HMAC_KEY:-}"
HMAC_KEY_FILE="${LAM_CIRCULATION_HMAC_KEY_FILE:-$ROOT/.gateway/security/circulation_hmac.key}"
HMAC_SECONDARY_KEY_ENV="${LAM_CIRCULATION_HMAC_SECONDARY_KEY:-}"
HMAC_SECONDARY_KEY_FILE="${LAM_CIRCULATION_HMAC_SECONDARY_KEY_FILE:-$ROOT/.gateway/security/circulation_hmac_prev.key}"
HMAC_ROTATION_STATE_FILE="${LAM_CIRCULATION_HMAC_ROTATION_STATE_FILE:-$ROOT/.gateway/security/circulation_hmac_rotation.json}"
HMAC_SECONDARY_GRACE_SEC="${LAM_CIRCULATION_HMAC_SECONDARY_GRACE_SEC:-86400}"
HMAC_SECONDARY_VALID_UNTIL_ENV="${LAM_CIRCULATION_HMAC_SECONDARY_VALID_UNTIL_EPOCH:-}"
ROOTKEY_KEY_FILE="${LAM_HUB_ROOT:-$ROOT/.gateway/hub}/rootkey_expected_sha256.txt"
HMAC_KEY_ID="${LAM_CIRCULATION_HMAC_KEY_ID:-rootkey-mirror-v1}"

mkdir -p "$OUTBOX_ROOT" "$INBOX_ROOT"
[[ -f "$SEEN_FILE" ]] || : > "$SEEN_FILE"

log() {
  printf '[lam-realtime-circulation] %s\n' "$*"
}

resolve_primary_hmac_key() {
  if [[ -n "$HMAC_KEY_ENV" ]]; then
    printf '%s' "$HMAC_KEY_ENV"
    return 0
  fi
  if [[ -f "$HMAC_KEY_FILE" ]]; then
    tr -d '\r\n' < "$HMAC_KEY_FILE"
    return 0
  fi
  if [[ -f "$ROOTKEY_KEY_FILE" ]]; then
    tr -d '\r\n' < "$ROOTKEY_KEY_FILE"
    return 0
  fi
  return 1
}

resolve_secondary_hmac_key() {
  if [[ -n "$HMAC_SECONDARY_KEY_ENV" ]]; then
    printf '%s' "$HMAC_SECONDARY_KEY_ENV"
    return 0
  fi
  if [[ -f "$HMAC_SECONDARY_KEY_FILE" ]]; then
    tr -d '\r\n' < "$HMAC_SECONDARY_KEY_FILE"
    return 0
  fi
  return 1
}

secondary_valid_until_epoch() {
  if [[ -n "$HMAC_SECONDARY_VALID_UNTIL_ENV" ]]; then
    printf '%s' "$HMAC_SECONDARY_VALID_UNTIL_ENV"
    return 0
  fi
  if [[ -f "$HMAC_ROTATION_STATE_FILE" ]]; then
    python3 - "$HMAC_ROTATION_STATE_FILE" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
try:
    obj = json.loads(p.read_text(encoding="utf-8"))
except Exception:
    print("")
    raise SystemExit(0)
print(str(obj.get("secondary_valid_until_epoch", "")).strip())
PY
    return 0
  fi
  if [[ -f "$HMAC_SECONDARY_KEY_FILE" && "$HMAC_SECONDARY_GRACE_SEC" =~ ^[0-9]+$ ]]; then
    local mtime
    mtime="$(stat -c %Y "$HMAC_SECONDARY_KEY_FILE" 2>/dev/null || printf '0')"
    if [[ "$mtime" =~ ^[0-9]+$ ]]; then
      printf '%s' "$((mtime + HMAC_SECONDARY_GRACE_SEC))"
      return 0
    fi
  fi
  printf ''
}

secondary_grace_active() {
  local deadline now
  deadline="$(secondary_valid_until_epoch)"
  [[ "$deadline" =~ ^[0-9]+$ ]] || return 1
  now="$(date +%s)"
  (( now <= deadline ))
}

latest_report_summaries() {
  find "$ROOT/.gateway/test_runs" -type f -name 'microtick_summary.json' 2>/dev/null \
    | sort \
    | tail -n "$REPORT_LIMIT"
}

build_inversion_report_bundle() {
  local ts out_file errors_file
  ts="$(date -u +%Y%m%dT%H%M%SZ)"
  out_file="$OUTBOX_ROOT/report_${ts}.json"
  errors_file="$ROOT/.gateway/test_runs/background/errors.jsonl"

  mapfile -t summaries < <(latest_report_summaries)
  python3 - "$out_file" "$NODE_ID" "$errors_file" "$ERROR_LINES" "${summaries[@]}" <<'PY'
import json, sys
from datetime import datetime, timezone
from pathlib import Path

out_file = Path(sys.argv[1])
node_id = sys.argv[2]
errors_file = Path(sys.argv[3])
error_lines = int(sys.argv[4])
summary_files = [Path(x) for x in sys.argv[5:]]

bundle = {
    "schema": "lam.inversion.test_reports.v1",
    "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "producer_node": node_id,
    "summaries": [],
    "background_errors_tail": [],
}

for p in summary_files:
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
        payload["_source_file"] = str(p)
        bundle["summaries"].append(payload)
    except Exception:
        continue

if errors_file.exists():
    lines = errors_file.read_text(encoding="utf-8").splitlines()
    bundle["background_errors_tail"] = lines[-error_lines:]

out_file.write_text(json.dumps(bundle, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
print(str(out_file))
PY
}

sign_inversion_bundle() {
  local bundle="$1"
  local sig_file="${bundle}.sig.json"
  local key
  if ! key="$(resolve_primary_hmac_key)"; then
    if [[ "$CRYPTO_REQUIRED" == "1" ]]; then
      log "crypto mirror: key missing (required)"
    else
      log "crypto mirror: key missing (optional)"
    fi
    return 1
  fi
  local sha hmac ts
  sha="$(sha256sum "$bundle" | awk '{print $1}')"
  hmac="$(openssl dgst -sha256 -hmac "$key" "$bundle" | awk '{print $2}')"
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  cat > "$sig_file" <<EOF
{
  "schema": "lam.inversion.sig.v1",
  "ts_utc": "$ts",
  "key_id": "$HMAC_KEY_ID",
  "sha256": "$sha",
  "hmac_sha256": "$hmac"
}
EOF
  log "crypto mirror: signed $(basename "$bundle")"
}

verify_inversion_bundle() {
  local bundle="$1"
  local sig_file="${bundle}.sig.json"
  if [[ ! -f "$sig_file" ]]; then
    [[ "$CRYPTO_REQUIRED" == "1" ]] && return 2 || return 0
  fi
  local key
  if ! key="$(resolve_primary_hmac_key)"; then
    [[ "$CRYPTO_REQUIRED" == "1" ]] && return 3 || return 0
  fi
  local sig_sha sig_hmac
  read -r sig_sha sig_hmac < <(python3 - "$sig_file" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1])
obj=json.loads(p.read_text(encoding="utf-8"))
print(str(obj.get("sha256","")).strip(), str(obj.get("hmac_sha256","")).strip())
PY
)
  local act_sha act_hmac
  act_sha="$(sha256sum "$bundle" | awk '{print $1}')"
  act_hmac="$(openssl dgst -sha256 -hmac "$key" "$bundle" | awk '{print $2}')"
  [[ -n "$sig_sha" && "$act_sha" == "$sig_sha" ]] || return 4
  if [[ -n "$sig_hmac" && "$act_hmac" == "$sig_hmac" ]]; then
    return 0
  fi
  local key_secondary act_hmac_secondary
  if key_secondary="$(resolve_secondary_hmac_key)"; then
    if ! secondary_grace_active; then
      return 6
    fi
    act_hmac_secondary="$(openssl dgst -sha256 -hmac "$key_secondary" "$bundle" | awk '{print $2}')"
    [[ -n "$sig_hmac" && "$act_hmac_secondary" == "$sig_hmac" ]] || return 5
    return 0
  fi
  return 5
}

ensure_hmac_key_seeded() {
  if resolve_primary_hmac_key >/dev/null 2>&1; then
    return 0
  fi
  if [[ -n "$HMAC_KEY_FILE" && ! -f "$HMAC_KEY_FILE" ]]; then
    mkdir -p "$(dirname "$HMAC_KEY_FILE")"
    openssl rand -hex 32 > "$HMAC_KEY_FILE"
    chmod 600 "$HMAC_KEY_FILE"
    log "crypto mirror: seeded new primary key at $HMAC_KEY_FILE"
  fi
  return 0
}

sync_push() {
  if "$ROOT/scripts/cloud_fabric.sh" sync-gdrive >/dev/null 2>&1; then
    log "push sync: ok"
  else
    log "push sync: skipped/fail (check CF_GDRIVE_ROOT)"
  fi
}

sync_pull() {
  if "$ROOT/scripts/cloud_fabric.sh" sync-from-gdrive >/dev/null 2>&1; then
    log "pull sync: ok"
  else
    log "pull sync: skipped/fail (check CF_GDRIVE_ROOT)"
  fi
}

already_seen_sha() {
  local sha="$1"
  rg -q "^${sha}[[:space:]]" "$SEEN_FILE" 2>/dev/null
}

mark_seen_sha() {
  local sha="$1" producer="$2" path="$3"
  printf '%s\t%s\t%s\t%s\n' "$sha" "$producer" "$path" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$SEEN_FILE"
}

ingest_inversion_reports() {
  local source_file producer rel sha target_dir target_file
  local base="$STATE_ROOT/inversion/outbox"
  [[ -d "$base" ]] || return 0
  while IFS= read -r source_file; do
    producer="$(basename "$(dirname "$source_file")")"
    [[ "$producer" == "$NODE_ID" ]] && continue
    rel="$(basename "$source_file")"
    sha="$(sha256sum "$source_file" | awk '{print $1}')"
    if already_seen_sha "$sha"; then
      continue
    fi
    local vrc=0
    if verify_inversion_bundle "$source_file"; then
      :
    else
      vrc=$?
      printf '{"ts_utc":"%s","event":"inversion_report_rejected_crypto","producer":"%s","rc":%d,"file":"%s"}\n' \
        "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$producer" "$vrc" "$source_file" >> "$INDEX_FILE"
      log "rejected by crypto verify rc=$vrc producer=$producer file=$rel"
      continue
    fi
    target_dir="$INBOX_ROOT/$producer"
    target_file="$target_dir/$rel"
    target_sig="$target_dir/${rel}.sig.json"
    mkdir -p "$target_dir"
    cp -f "$source_file" "$target_file"
    [[ -f "${source_file}.sig.json" ]] && cp -f "${source_file}.sig.json" "$target_sig" || true
    mark_seen_sha "$sha" "$producer" "$target_file"
    printf '{"ts_utc":"%s","event":"inversion_report_ingested","producer":"%s","sha256":"%s","file":"%s"}\n' \
      "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$producer" "$sha" "$target_file" >> "$INDEX_FILE"
    log "ingested report from producer=$producer file=$rel"
  done < <(find "$base" -mindepth 2 -maxdepth 2 -type f -name 'report_*.json' | sort)
}

run_cycle() {
  local bundle_file
  ensure_hmac_key_seeded
  bundle_file="$(build_inversion_report_bundle)"
  log "bundle exported: $bundle_file"
  sign_inversion_bundle "$bundle_file" || true
  sync_push
  sync_pull
  ingest_inversion_reports
}

usage() {
  cat <<'EOF'
Usage:
  scripts/lam_realtime_circulation.sh --once
  scripts/lam_realtime_circulation.sh --daemon [--interval-sec N]
  scripts/lam_realtime_circulation.sh --status
EOF
}

if [[ "${1:-}" == "--once" ]]; then
  run_cycle
  exit 0
fi

if [[ "${1:-}" == "--status" ]]; then
  printf "node_id=%s\n" "$NODE_ID"
  printf "state_root=%s\n" "$STATE_ROOT"
  printf "outbox=%s\n" "$OUTBOX_ROOT"
  printf "inbox=%s\n" "$INBOX_ROOT"
  printf "seen=%s\n" "$SEEN_FILE"
  printf "crypto_required=%s\n" "$CRYPTO_REQUIRED"
  printf "hmac_key_file=%s\n" "$HMAC_KEY_FILE"
  printf "hmac_secondary_key_file=%s\n" "$HMAC_SECONDARY_KEY_FILE"
  printf "hmac_rotation_state_file=%s\n" "$HMAC_ROTATION_STATE_FILE"
  printf "hmac_secondary_grace_sec=%s\n" "$HMAC_SECONDARY_GRACE_SEC"
  exit 0
fi

if [[ "${1:-}" == "--daemon" ]]; then
  shift || true
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --interval-sec)
        INTERVAL_SEC="$2"; shift 2 ;;
      *)
        echo "unknown arg: $1" >&2; exit 2 ;;
    esac
  done
  log "daemon started interval_sec=$INTERVAL_SEC node_id=$NODE_ID"
  while true; do
    run_cycle || true
    sleep "$INTERVAL_SEC"
  done
fi

usage
exit 2
