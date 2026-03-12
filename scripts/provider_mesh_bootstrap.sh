#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${LAM_PROVIDER_ENV_FILE:-$ROOT/scripts/provider-secrets.env}"
STATE_FILE="${LAM_HUB_ROOT:-$ROOT/.gateway/hub}/provider_mesh_bootstrap_state.json"
MODE="${1:-status}"

usage() {
  cat <<'EOF'
Usage:
  scripts/provider_mesh_bootstrap.sh verify
  scripts/provider_mesh_bootstrap.sh apply
  scripts/provider_mesh_bootstrap.sh status

Env:
  LAM_PROVIDER_ENV_FILE=/path/to/provider-secrets.env
EOF
}

load_env() {
  if [[ -f "$ENV_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    return 0
  fi
  return 1
}

bool_json() {
  [[ "${1:-}" == "1" ]] && printf 'true' || printf 'false'
}

verify_env() {
  local has_env=0
  local has_gws=0 has_onedrive=0 has_openai=0 has_anthropic=0 has_xai=0 has_shinkai=0 has_ollama=0
  if load_env; then
    has_env=1
  fi
  [[ -n "${LAM_GWS_DRIVE_ROOT:-}" ]] && has_gws=1
  [[ -n "${GATEWAY_ONEDRIVE_ROOT:-}" ]] && has_onedrive=1
  [[ -n "${OPENAI_API_KEY:-}" ]] && has_openai=1
  [[ -n "${ANTHROPIC_API_KEY:-}" ]] && has_anthropic=1
  [[ -n "${XAI_API_KEY:-}" ]] && has_xai=1
  [[ -n "${SHINKAI_API_URL:-}" ]] && has_shinkai=1
  if command -v ollama >/dev/null 2>&1 || ss -ltn 2>/dev/null | rg -q ':11434'; then
    has_ollama=1
  fi

  local now
  now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  mkdir -p "$(dirname "$STATE_FILE")"
  cat > "$STATE_FILE" <<EOF
{
  "ts_utc": "$now",
  "env_file": "$ENV_FILE",
  "env_file_present": $(bool_json "$has_env"),
  "signals": {
    "gws_root_configured": $(bool_json "$has_gws"),
    "onedrive_root_configured": $(bool_json "$has_onedrive"),
    "openai_key_present": $(bool_json "$has_openai"),
    "anthropic_key_present": $(bool_json "$has_anthropic"),
    "xai_key_present": $(bool_json "$has_xai"),
    "shinkai_url_present": $(bool_json "$has_shinkai"),
    "ollama_available": $(bool_json "$has_ollama")
  }
}
EOF
  cat "$STATE_FILE"
}

apply_env() {
  if ! load_env; then
    echo "[provider-mesh-bootstrap] env file not found: $ENV_FILE" >&2
    echo "[provider-mesh-bootstrap] copy from scripts/provider-secrets.env.example" >&2
    exit 1
  fi
  [[ -n "${LAM_GWS_DRIVE_ROOT:-}" ]] && mkdir -p "$LAM_GWS_DRIVE_ROOT" || true
  [[ -n "${GATEWAY_ONEDRIVE_ROOT:-}" ]] && mkdir -p "$GATEWAY_ONEDRIVE_ROOT" || true
  verify_env >/dev/null
  "$ROOT/scripts/lam_external_provider_mesh.sh" --once >/dev/null || true
  "$ROOT/scripts/lam_gws_bridge.sh" --once >/dev/null || true
  "$ROOT/scripts/lam_feedback_gateway.sh" --once >/dev/null || true
  echo "[provider-mesh-bootstrap] apply complete"
  cat "$STATE_FILE"
}

status_env() {
  if [[ -f "$STATE_FILE" ]]; then
    cat "$STATE_FILE"
  else
    echo "{}"
  fi
}

case "$MODE" in
  verify) verify_env ;;
  apply) apply_env ;;
  status) status_env ;;
  -h|--help) usage ;;
  *) usage; exit 2 ;;
esac

