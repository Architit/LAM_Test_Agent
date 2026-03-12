#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HUB_ROOT="${LAM_HUB_ROOT:-$ROOT/.gateway/hub}"
STATE_FILE="$HUB_ROOT/role_orchestrator_state.json"
PROFILES_FILE="$ROOT/infra/security/role_profiles.json"
PROFILE_OVERRIDE_FILE="$HUB_ROOT/role_profile.override"

cmd="${1:-status}"

case "$cmd" in
  status)
    if [[ -f "$STATE_FILE" ]]; then
      cat "$STATE_FILE"
    else
      echo '{"status":"no_state"}'
    fi
    ;;
  profiles)
    cat "$PROFILES_FILE"
    ;;
  set-profile)
    profile="${2:-}"
    [[ -n "$profile" ]] || { echo "usage: $0 set-profile <name>" >&2; exit 2; }
    mkdir -p "$HUB_ROOT"
    printf '%s\n' "$profile" > "$PROFILE_OVERRIDE_FILE"
    echo "profile_override=$profile file=$PROFILE_OVERRIDE_FILE"
    ;;
  rebind-now)
    "$ROOT/scripts/lam_role_orchestrator.sh" --once --force-wake
    ;;
  *)
    echo "Usage: $0 [status|profiles|set-profile <name>|rebind-now]" >&2
    exit 2
    ;;
esac
