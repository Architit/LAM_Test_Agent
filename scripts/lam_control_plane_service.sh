#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHECK_INTERVAL_SEC="${LAM_CONTROL_PLANE_CHECK_INTERVAL_SEC:-10}"
HUB_ROOT="${LAM_HUB_ROOT:-$ROOT/.gateway/hub}"
LOCKDOWN_FILE="${LAM_SECURITY_LOCKDOWN_FILE:-$HUB_ROOT/security_lockdown.flag}"

required_services() {
  local out=("model_worker" "portal_gateway")
  if [[ "${LAM_ENABLE_MCP_WATCHDOG:-1}" == "1" ]]; then
    out+=("mcp_watchdog")
  fi
  if [[ "${LAM_ENABLE_GWS_BRIDGE:-1}" == "1" ]]; then
    out+=("gws_bridge")
  fi
  if [[ "${LAM_ENABLE_SECURITY_GUARD:-1}" == "1" ]]; then
    out+=("security_guard")
  fi
  if [[ "${LAM_ENABLE_ROLE_ORCHESTRATOR:-1}" == "1" ]]; then
    out+=("role_orchestrator")
  fi
  if [[ "${LAM_ENABLE_POWER_FABRIC:-1}" == "1" ]]; then
    out+=("power_fabric_guard")
  fi
  if [[ "${LAM_ENABLE_REALTIME_CIRCULATION:-1}" == "1" ]]; then
    out+=("realtime_circulation")
  fi
  if [[ "${LAM_ENABLE_DEVICE_MESH:-1}" == "1" ]]; then
    out+=("device_mesh_daemon")
  fi
  if [[ "${LAM_ENABLE_ACTIVITY_TELEMETRY:-1}" == "1" ]]; then
    out+=("activity_telemetry")
  fi
  if [[ "${LAM_ENABLE_AMBIENT_LIGHT:-1}" == "1" ]]; then
    out+=("ambient_light")
  fi
  if [[ "${LAM_ENABLE_IO_SPECTRAL:-1}" == "1" ]]; then
    out+=("io_spectral")
  fi
  if [[ "${LAM_ENABLE_GOVERNANCE_AUTOPILOT:-1}" == "1" ]]; then
    out+=("governance_autopilot")
  fi
  if [[ "${LAM_ENABLE_MEDIA_SYNC:-1}" == "1" ]]; then
    out+=("media_sync")
  fi
  if [[ "${LAM_ENABLE_ROOTKEY_GATE:-1}" == "1" ]]; then
    out+=("rootkey_gate")
  fi
  if [[ "${LAM_ENABLE_FAILSAFE_GUARD:-1}" == "1" ]]; then
    out+=("failsafe_guard")
  fi
  if [[ "${LAM_ENABLE_EXTERNAL_PROVIDER_MESH:-1}" == "1" ]]; then
    out+=("external_provider_mesh")
  fi
  if [[ "${LAM_ENABLE_FEEDBACK_GATEWAY:-1}" == "1" ]]; then
    out+=("feedback_gateway")
  fi
  printf '%s\n' "${out[@]}"
}

is_running() {
  local name="$1"
  local pid_dir="${LAM_STACK_PID_DIR:-$ROOT/.gateway/hub/pids}"
  local pid_file="$pid_dir/${name}.pid"
  [[ -f "$pid_file" ]] || return 1
  kill -0 "$(cat "$pid_file")" >/dev/null 2>&1
}

all_running() {
  local name
  while IFS= read -r name; do
    [[ -n "$name" ]] || continue
    if ! is_running "$name"; then
      return 1
    fi
  done < <(required_services)
  return 0
}

start_stack() {
  "$ROOT/scripts/lam_bridge_stack.sh" start
}

stop_stack() {
  "$ROOT/scripts/lam_bridge_stack.sh" stop || true
}

on_exit() {
  stop_stack
}
trap on_exit EXIT INT TERM

if [[ -f "$LOCKDOWN_FILE" ]]; then
  echo "[lam-control-plane] startup blocked by security lockdown: $LOCKDOWN_FILE"
else
  start_stack
fi

while true; do
  if [[ -f "$LOCKDOWN_FILE" ]]; then
    echo "[lam-control-plane] security lockdown flag detected: $LOCKDOWN_FILE"
    stop_stack
    sleep "$CHECK_INTERVAL_SEC"
    continue
  fi
  if ! all_running; then
    echo "[lam-control-plane] detected service drift; restarting stack"
    "$ROOT/scripts/lam_bridge_stack.sh" restart
  fi
  sleep "$CHECK_INTERVAL_SEC"
done
