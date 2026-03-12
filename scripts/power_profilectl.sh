#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HUB_ROOT="${LAM_HUB_ROOT:-$ROOT/.gateway/hub}"
OVERRIDE_FILE="$HUB_ROOT/power_profile.override"
STATE_FILE="$HUB_ROOT/power_fabric_state.json"
SYSTEM_ENV_FILE="/etc/default/lam-control-plane"

usage() {
  cat <<'EOF'
Usage:
  scripts/power_profilectl.sh status
  scripts/power_profilectl.sh set <auto|turbo|balanced|quiet> [--system]
  scripts/power_profilectl.sh clear [--system]
  scripts/power_profilectl.sh show

Notes:
  - Local mode writes: LAM_HUB_ROOT/power_profile.override
  - --system mode updates /etc/default/lam-control-plane (root required)
EOF
}

require_root() {
  [[ "${EUID}" -eq 0 ]] || { echo "[power-profilectl] root required for --system"; exit 1; }
}

set_local_profile() {
  local profile="$1"
  mkdir -p "$HUB_ROOT"
  printf '%s\n' "$profile" > "$OVERRIDE_FILE"
  echo "[power-profilectl] local profile set: $profile ($OVERRIDE_FILE)"
}

clear_local_profile() {
  rm -f "$OVERRIDE_FILE"
  echo "[power-profilectl] local profile cleared"
}

set_system_profile() {
  local profile="$1"
  require_root
  touch "$SYSTEM_ENV_FILE"
  if grep -q '^LAM_POWER_PROFILE_OVERRIDE=' "$SYSTEM_ENV_FILE"; then
    sed -i "s/^LAM_POWER_PROFILE_OVERRIDE=.*/LAM_POWER_PROFILE_OVERRIDE=$profile/" "$SYSTEM_ENV_FILE"
  else
    printf '\nLAM_POWER_PROFILE_OVERRIDE=%s\n' "$profile" >> "$SYSTEM_ENV_FILE"
  fi
  echo "[power-profilectl] system profile set: $profile ($SYSTEM_ENV_FILE)"
}

clear_system_profile() {
  require_root
  if [[ -f "$SYSTEM_ENV_FILE" ]]; then
    sed -i '/^LAM_POWER_PROFILE_OVERRIDE=/d' "$SYSTEM_ENV_FILE"
  fi
  echo "[power-profilectl] system profile cleared ($SYSTEM_ENV_FILE)"
}

show_profile() {
  local local_profile="auto"
  local system_profile="(unset)"
  if [[ -f "$OVERRIDE_FILE" ]]; then
    local_profile="$(tr '[:upper:]' '[:lower:]' < "$OVERRIDE_FILE" | xargs)"
  fi
  if [[ -f "$SYSTEM_ENV_FILE" ]]; then
    system_profile="$(awk -F= '/^LAM_POWER_PROFILE_OVERRIDE=/{print $2}' "$SYSTEM_ENV_FILE" | tail -n1)"
    [[ -n "$system_profile" ]] || system_profile="(unset)"
  fi
  echo "local_profile=$local_profile"
  echo "system_profile=$system_profile"
}

status() {
  show_profile
  if [[ -f "$STATE_FILE" ]]; then
    python3 - <<'PY' "$STATE_FILE"
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
data = json.loads(p.read_text(encoding="utf-8"))
print(f"runtime_mode={data.get('mode','unknown')}")
print(f"runtime_manual_profile={data.get('manual_profile','auto')}")
print(f"runtime_ts_utc={data.get('ts_utc','')}")
PY
  else
    echo "runtime_state=not_available"
  fi
}

CMD="${1:-status}"
shift || true

case "$CMD" in
  set)
    PROFILE="${1:-}"
    [[ "$PROFILE" =~ ^(auto|turbo|balanced|quiet)$ ]] || { usage; exit 2; }
    shift || true
    SYSTEM_MODE=0
    if [[ "${1:-}" == "--system" ]]; then
      SYSTEM_MODE=1
    fi
    set_local_profile "$PROFILE"
    if [[ "$SYSTEM_MODE" == "1" ]]; then
      set_system_profile "$PROFILE"
    fi
    ;;
  clear)
    SYSTEM_MODE=0
    if [[ "${1:-}" == "--system" ]]; then
      SYSTEM_MODE=1
    fi
    clear_local_profile
    if [[ "$SYSTEM_MODE" == "1" ]]; then
      clear_system_profile
    fi
    ;;
  show)
    show_profile
    ;;
  status)
    status
    ;;
  *)
    usage
    exit 2
    ;;
esac
