#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAME="$(basename "$ROOT")"
STATE_ROOT="${AESS_STATE_ROOT:-/tmp/aess_autostart}"
LOG_DIR="$STATE_ROOT/logs"
LOCK_DIR="$STATE_ROOT/locks"
COOLDOWN_SEC="${AESS_REPO_COOLDOWN_SEC:-300}"
DEFAULT_AGENT_ID="${AESS_DEFAULT_AGENT_ID:-lam_test_agent}"
DEFAULT_AGENTS_FILE="${AESS_DEFAULT_AGENTS_FILE:-$STATE_ROOT/default_agents.list}"
REPO_DEFAULT_AGENT_ID="$(printf '%s' "$NAME" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/_/g; s/^_+//; s/_+$//')"
DEFAULT_AGENT_IDS_RAW="${AESS_DEFAULT_AGENT_IDS:-${DEFAULT_AGENT_ID},${REPO_DEFAULT_AGENT_ID}}"
STAMP_FILE="$STATE_ROOT/${NAME}.last"
LOCK_FILE="$LOCK_DIR/${NAME}.lock"

mkdir -p "$LOG_DIR" "$LOCK_DIR"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "SKIP ${NAME}: lock active"
  exit 0
fi

now="$(date +%s)"
if [[ -f "$STAMP_FILE" ]]; then
  last="$(cat "$STAMP_FILE" 2>/dev/null || echo 0)"
  if [[ "$last" =~ ^[0-9]+$ ]]; then
    delta=$(( now - last ))
    if (( delta < COOLDOWN_SEC )); then
      echo "SKIP ${NAME}: cooldown ${delta}s < ${COOLDOWN_SEC}s"
      exit 0
    fi
  fi
fi
echo "$now" > "$STAMP_FILE"

log="$LOG_DIR/${NAME}.log"
{
  echo "[$(date -Iseconds)] aess_autostart begin repo=${NAME}"
  if [[ ! -f "$DEFAULT_AGENTS_FILE" ]]; then
    touch "$DEFAULT_AGENTS_FILE"
  fi
  IFS=',' read -r -a _aess_default_ids <<< "$DEFAULT_AGENT_IDS_RAW"
  for _id in "${_aess_default_ids[@]}"; do
    _id="$(printf '%s' "$_id" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')"
    if [[ -z "$_id" ]]; then
      continue
    fi
    if ! grep -Fxq "$_id" "$DEFAULT_AGENTS_FILE"; then
      echo "$_id" >> "$DEFAULT_AGENTS_FILE"
      echo "[$(date -Iseconds)] default-agent:added id=$_id file=$DEFAULT_AGENTS_FILE"
    else
      echo "[$(date -Iseconds)] default-agent:exists id=$_id file=$DEFAULT_AGENTS_FILE"
    fi
  done
  if [[ -x "$ROOT/scripts/aess_service_start.sh" ]]; then
    echo "[$(date -Iseconds)] running scripts/aess_service_start.sh"
    "$ROOT/scripts/aess_service_start.sh"
    echo "[$(date -Iseconds)] service start script completed"
  else
    echo "[$(date -Iseconds)] NO_SERVICE_DEFINED (create scripts/aess_service_start.sh to enable runtime start)"
  fi
  echo "[$(date -Iseconds)] aess_autostart end"
} >> "$log" 2>&1

echo "OK ${NAME}: autostart contract processed"
