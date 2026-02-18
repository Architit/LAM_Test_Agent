#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_NAME="$(basename "$ROOT")"

GATEWAY_GITHUB_REMOTE="${GATEWAY_GITHUB_REMOTE:-origin}"
GATEWAY_ONEDRIVE_ROOT="${GATEWAY_ONEDRIVE_ROOT:-}"
GATEWAY_GWORKSPACE_ROOT="${GATEWAY_GWORKSPACE_ROOT:-}"
GATEWAY_EXPORT_DIR="${GATEWAY_EXPORT_DIR:-$ROOT/.gateway/export}"
GATEWAY_IMPORT_DIR="${GATEWAY_IMPORT_DIR:-$ROOT/.gateway/import}"
GATEWAY_STAGE_DIR="$ROOT/.gateway/import_staging"
LAM_EXTERNAL_DEBUG_LOG_DIR="${LAM_EXTERNAL_DEBUG_LOG_DIR:-$ROOT/.gateway/external_debug}"
LAM_EXTERNAL_DEBUG_FILE="${LAM_EXTERNAL_DEBUG_FILE:-codex_openai_codefix_debug.jsonl}"
OPENAI_DEBUG_UPLOAD_URL="${OPENAI_DEBUG_UPLOAD_URL:-}"
OPENAI_DEBUG_TIMEOUT_SEC="${OPENAI_DEBUG_TIMEOUT_SEC:-60}"
OPENAI_DEBUG_RECEIPTS_DIR="${OPENAI_DEBUG_RECEIPTS_DIR:-$ROOT/.gateway/receipts}"

log() { echo "[$(date -Iseconds)] $*"; }

verify_github() {
  if git -C "$ROOT" remote get-url "$GATEWAY_GITHUB_REMOTE" >/dev/null 2>&1; then
    log "github:ok remote=$GATEWAY_GITHUB_REMOTE"
  else
    log "github:fail remote_not_found remote=$GATEWAY_GITHUB_REMOTE"
    return 1
  fi
}

verify_onedrive() {
  if [[ -z "$GATEWAY_ONEDRIVE_ROOT" ]]; then
    log "onedrive:warn env_not_set GATEWAY_ONEDRIVE_ROOT"
    return 2
  fi
  if [[ -d "$GATEWAY_ONEDRIVE_ROOT" ]]; then
    log "onedrive:ok path=$GATEWAY_ONEDRIVE_ROOT"
  else
    log "onedrive:fail path_missing path=$GATEWAY_ONEDRIVE_ROOT"
    return 1
  fi
}

verify_gworkspace() {
  if [[ -z "$GATEWAY_GWORKSPACE_ROOT" ]]; then
    log "gworkspace:warn env_not_set GATEWAY_GWORKSPACE_ROOT"
    return 2
  fi
  if [[ -d "$GATEWAY_GWORKSPACE_ROOT" ]]; then
    log "gworkspace:ok path=$GATEWAY_GWORKSPACE_ROOT"
  else
    log "gworkspace:fail path_missing path=$GATEWAY_GWORKSPACE_ROOT"
    return 1
  fi
}

do_export() {
  mkdir -p "$GATEWAY_EXPORT_DIR"
  ts="$(date +%Y%m%d_%H%M%S)"
  archive="$GATEWAY_EXPORT_DIR/${REPO_NAME}_${ts}.tgz"
  tar --exclude='.git' --exclude='.venv' --exclude='__pycache__' -czf "$archive" -C "$ROOT" .
  log "export:ok archive=$archive"
}

do_import() {
  local archive="${1:-}"
  if [[ -z "$archive" ]]; then
    log "import:fail missing_archive_argument"
    return 1
  fi
  if [[ ! -f "$archive" ]]; then
    log "import:fail archive_not_found path=$archive"
    return 1
  fi
  mkdir -p "$GATEWAY_IMPORT_DIR" "$GATEWAY_STAGE_DIR"
  cp -f "$archive" "$GATEWAY_IMPORT_DIR/"
  find "$GATEWAY_STAGE_DIR" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
  tar -xzf "$archive" -C "$GATEWAY_STAGE_DIR"
  log "import:ok staged_at=$GATEWAY_STAGE_DIR archive=$(basename "$archive")"
}

debug_log_path() {
  local candidate="${1:-}"
  if [[ -n "$candidate" ]]; then
    echo "$candidate"
    return 0
  fi
  echo "$LAM_EXTERNAL_DEBUG_LOG_DIR/$LAM_EXTERNAL_DEBUG_FILE"
}

do_export_debug() {
  local input
  input="$(debug_log_path "${1:-}")"
  if [[ ! -f "$input" ]]; then
    log "export-debug:fail debug_log_not_found path=$input"
    return 1
  fi
  mkdir -p "$GATEWAY_EXPORT_DIR"
  local ts archive
  ts="$(date +%Y%m%d_%H%M%S)"
  archive="$GATEWAY_EXPORT_DIR/${REPO_NAME}_codex_openai_debug_${ts}.tgz"
  tar -czf "$archive" -C "$(dirname "$input")" "$(basename "$input")"
  log "export-debug:ok archive=$archive source=$input"
}

do_send_openai_debug() {
  local input
  input="$(debug_log_path "${1:-}")"
  if [[ ! -f "$input" ]]; then
    log "send-openai-debug:fail debug_log_not_found path=$input"
    return 1
  fi
  if [[ -z "$OPENAI_DEBUG_UPLOAD_URL" ]]; then
    log "send-openai-debug:fail missing_env OPENAI_DEBUG_UPLOAD_URL"
    return 1
  fi
  if ! command -v curl >/dev/null 2>&1; then
    log "send-openai-debug:fail curl_not_found"
    return 1
  fi

  local response_tmp status auth_header
  response_tmp="$(mktemp)"
  auth_header=()
  if [[ -n "${OPENAI_API_KEY:-}" ]]; then
    auth_header=(-H "Authorization: Bearer $OPENAI_API_KEY")
  fi

  status="$(
    curl -sS -o "$response_tmp" -w "%{http_code}" \
      --connect-timeout "$OPENAI_DEBUG_TIMEOUT_SEC" \
      --max-time "$OPENAI_DEBUG_TIMEOUT_SEC" \
      -X POST "$OPENAI_DEBUG_UPLOAD_URL" \
      "${auth_header[@]}" \
      -H "Content-Type: application/jsonl" \
      --data-binary "@$input"
  )"

  mkdir -p "$OPENAI_DEBUG_RECEIPTS_DIR"
  local ts receipt sha body
  ts="$(date +%Y%m%d_%H%M%S)"
  receipt="$OPENAI_DEBUG_RECEIPTS_DIR/openai_debug_send_receipt_${ts}.json"
  sha="$(sha256sum "$input" | awk '{print $1}')"
  body="$(tr '\n' ' ' < "$response_tmp" | head -c 1500)"
  cat > "$receipt" <<EOF
{
  "ts_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "repo": "$REPO_NAME",
  "source_file": "$input",
  "sha256": "$sha",
  "upload_url": "$OPENAI_DEBUG_UPLOAD_URL",
  "http_status": "$status",
  "response_preview": $(printf '%s' "$body" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')
}
EOF
  rm -f "$response_tmp"

  if [[ "$status" =~ ^2[0-9][0-9]$ ]]; then
    log "send-openai-debug:ok status=$status receipt=$receipt"
    return 0
  fi

  log "send-openai-debug:fail status=$status receipt=$receipt"
  return 1
}

cmd="${1:-verify}"
case "$cmd" in
  verify)
    rc=0
    verify_github || rc=1
    verify_onedrive || true
    verify_gworkspace || true
    exit "$rc"
    ;;
  export)
    do_export
    ;;
  import)
    do_import "${2:-}"
    ;;
  export-debug)
    do_export_debug "${2:-}"
    ;;
  send-openai-debug)
    do_send_openai_debug "${2:-}"
    ;;
  *)
    echo "Usage: $0 [verify|export|import <archive>|export-debug [log_file]|send-openai-debug [log_file]]"
    exit 2
    ;;
esac
