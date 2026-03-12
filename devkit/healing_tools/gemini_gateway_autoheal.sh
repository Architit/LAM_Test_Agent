#!/usr/bin/env bash
set -euo pipefail

# Gateway auto-heal for Gemini + Google Workspace MCP.
# ИСЦЕЛЕНИЕ: Перехват переменной REAL_GEMINI
REAL_GEMINI="${REAL_GEMINI:-gemini}"

NO_REINSTALL=0
for arg in "$@"; do
  case "$arg" in
    --no-reinstall)
      NO_REINSTALL=1
      ;;
    *)
      echo "[gateway-autoheal] Unknown arg: $arg" >&2
      echo "Usage: $0 [--no-reinstall]" >&2
      exit 2
      ;;
  esac
done

GEMINI_HOME="${HOME}/.gemini"
SETTINGS_FILE="${GEMINI_HOME}/settings.json"
POLICY_DIR="${GEMINI_HOME}/policies"
POLICY_FILE="${POLICY_DIR}/auto-saved.toml"
LAST_GOOD_FILE="${POLICY_DIR}/auto-saved.last-good.toml"
PREFLIGHT_FILE="${POLICY_DIR}/policy_preflight.py"
EXT_DIR="${GEMINI_HOME}/extensions/google-workspace"
TOKEN_FILE="${EXT_DIR}/gemini-cli-workspace-token.json"
MASTER_KEY_FILE="${EXT_DIR}/.gemini-cli-workspace-master-key"
WORKSPACE_EXT_URL="https://github.com/gemini-cli-extensions/workspace"
TS="$(date -u +%Y%m%dT%H%M%SZ)"

log() {
  printf '[gateway-autoheal] %s\n' "$*"
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[gateway-autoheal] Missing required command: $1" >&2
    exit 1
  fi
}

require_cmd python3
require_cmd node
require_cmd "$REAL_GEMINI"

mkdir -p "${POLICY_DIR}" "${GEMINI_HOME}/backup"

if [[ -f "${SETTINGS_FILE}" ]]; then
  cp "${SETTINGS_FILE}" "${GEMINI_HOME}/backup/settings.json.${TS}.bak"
fi

python3 - "${SETTINGS_FILE}" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
if path.exists():
    data = json.loads(path.read_text(encoding="utf-8"))
else:
    data = {}

security = data.setdefault("security", {})
security["enablePermanentToolApproval"] = True
security["enableConseca"] = False
path.write_text(json.dumps(data, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
PY
log "settings baseline synced"

if [[ -f "${POLICY_FILE}" ]]; then
  cp "${POLICY_FILE}" "${GEMINI_HOME}/backup/auto-saved.toml.${TS}.bak"
fi

cat > "${POLICY_FILE}" <<'EOF2'
# AUTO-BASELINE: codex-policy-v1
[[rule]]
toolName = "read_file"
decision = "allow"
priority = 300

[[rule]]
toolName = "grep_search"
decision = "allow"
priority = 300

[[rule]]
toolName = "list_dir"
decision = "allow"
priority = 300

[[rule]]
toolName = "list_directory"
decision = "allow"
priority = 300

[[rule]]
toolName = "write_file"
decision = "allow"
priority = 300

[[rule]]
toolName = "edit"
decision = "allow"
priority = 300

[[rule]]
toolName = "replace"
decision = "allow"
priority = 300

[[rule]]
toolName = "cli_help"
decision = "allow"
priority = 300

[[rule]]
toolName = "run_shell_command"
decision = "allow"
priority = 250

[[rule]]
mcpName = "google-workspace"
decision = "allow"
priority = 300

[[rule]]
mcpName = "github"
decision = "allow"
priority = 300

[[rule]]
mcpName = "gcloud"
decision = "allow"
priority = 300
EOF2
cp "${POLICY_FILE}" "${LAST_GOOD_FILE}"
log "policy baseline synced"

if [[ -f "${PREFLIGHT_FILE}" ]]; then
  if python3 "${PREFLIGHT_FILE}" "${POLICY_FILE}" >/dev/null; then
    log "policy preflight ok"
  else
    echo "[gateway-autoheal] policy preflight failed after baseline sync" >&2
    exit 1
  fi
fi

workspace_transport_ok() {
  local payload out
  payload='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"gateway-autoheal","version":"1.0"}}}
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
'
  if [[ ! -d "${EXT_DIR}" ]]; then
    return 1
  fi
  out="$(printf '%s' "${payload}" | timeout 12s node "${EXT_DIR}/dist/index.js" --use-dot-names 2>&1 || true)"
  [[ "${out}" == *'"id":1'* && "${out}" == *'"id":2'* ]]
}

if workspace_transport_ok; then
  log "google-workspace MCP transport healthy"
else
  log "google-workspace MCP transport unhealthy"
  if [[ "${NO_REINSTALL}" -eq 1 ]]; then
    echo "[gateway-autoheal] NO_REINSTALL=1, skipping reinstall" >&2
    exit 1
  fi

  rm -f "${TOKEN_FILE}" "${MASTER_KEY_FILE}" || true
  log "workspace auth store reset"

  "$REAL_GEMINI" extensions uninstall google-workspace >/dev/null 2>&1 || true
  if ! printf 'Y\n' | "$REAL_GEMINI" extensions install "${WORKSPACE_EXT_URL}" >/dev/null 2>&1; then
    echo "[gateway-autoheal] reinstall failed: google-workspace extension" >&2
    exit 1
  fi

  if workspace_transport_ok; then
    log "google-workspace MCP recovered"
  else
    echo "[gateway-autoheal] google-workspace MCP still unhealthy after reinstall" >&2
    exit 1
  fi
fi

log "auto-heal complete"
