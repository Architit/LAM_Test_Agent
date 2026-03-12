#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-start}"
PROVIDER_ENV_FILE="${LAM_PROVIDER_ENV_FILE:-$ROOT/scripts/provider-secrets.env}"
if [[ -f "$PROVIDER_ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$PROVIDER_ENV_FILE"
fi
PORT="${LAM_PORTAL_PORT:-8765}"
PORTAL_MODE="${LAM_PORTAL_MODE:-file}"
ENABLE_MCP_WATCHDOG="${LAM_ENABLE_MCP_WATCHDOG:-1}"
ENABLE_GWS_BRIDGE="${LAM_ENABLE_GWS_BRIDGE:-1}"
ENABLE_SECURITY_GUARD="${LAM_ENABLE_SECURITY_GUARD:-1}"
ENABLE_ROLE_ORCHESTRATOR="${LAM_ENABLE_ROLE_ORCHESTRATOR:-1}"
ENABLE_REALTIME_CIRCULATION="${LAM_ENABLE_REALTIME_CIRCULATION:-1}"
ENABLE_POWER_FABRIC="${LAM_ENABLE_POWER_FABRIC:-1}"
ENABLE_DEVICE_MESH="${LAM_ENABLE_DEVICE_MESH:-1}"
ENABLE_ACTIVITY_TELEMETRY="${LAM_ENABLE_ACTIVITY_TELEMETRY:-1}"
ENABLE_AMBIENT_LIGHT="${LAM_ENABLE_AMBIENT_LIGHT:-1}"
ENABLE_IO_SPECTRAL="${LAM_ENABLE_IO_SPECTRAL:-1}"
ENABLE_GOVERNANCE_AUTOPILOT="${LAM_ENABLE_GOVERNANCE_AUTOPILOT:-1}"
ENABLE_MEDIA_SYNC="${LAM_ENABLE_MEDIA_SYNC:-1}"
ENABLE_ROOTKEY_GATE="${LAM_ENABLE_ROOTKEY_GATE:-1}"
ENABLE_FAILSAFE_GUARD="${LAM_ENABLE_FAILSAFE_GUARD:-1}"
ENABLE_EXTERNAL_PROVIDER_MESH="${LAM_ENABLE_EXTERNAL_PROVIDER_MESH:-1}"
ENABLE_FEEDBACK_GATEWAY="${LAM_ENABLE_FEEDBACK_GATEWAY:-1}"
APPLY_CIRCULATION_POLICY_ON_START="${LAM_APPLY_CIRCULATION_POLICY_ON_START:-1}"
PID_DIR="${LAM_STACK_PID_DIR:-$ROOT/.gateway/hub/pids}"
LOG_DIR="${LAM_STACK_LOG_DIR:-$ROOT/.gateway/hub/logs}"

mkdir -p "$PID_DIR" "$LOG_DIR"

start_proc() {
  local name="$1"
  shift
  local pid_file="$PID_DIR/${name}.pid"
  if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" >/dev/null 2>&1; then
    echo "[lam-bridge-stack] $name already running"
    return 0
  fi
  nohup env PYTHONPATH="$ROOT:${PYTHONPATH:-}" "$@" >"$LOG_DIR/${name}.log" 2>&1 &
  echo "$!" >"$pid_file"
  echo "[lam-bridge-stack] started $name pid=$(cat "$pid_file")"
}

apply_circulation_policy() {
  if [[ "$APPLY_CIRCULATION_POLICY_ON_START" != "1" ]]; then
    return 0
  fi
  local policy_file="${LAM_GATEWAY_POLICY_FILE:-$ROOT/.gateway/routing_policy.json}"
  local template_file="${LAM_CIRCULATION_POLICY_TEMPLATE:-$ROOT/infra/governance/GATEWAY_CIRCULATION_POLICY_TEMPLATE.json}"
  if [[ ! -f "$template_file" ]]; then
    echo "[lam-bridge-stack] circulation template not found, skip: $template_file"
    return 0
  fi
  if python3 "$ROOT/scripts/gateway_apply_circulation_policy.py" --policy-file "$policy_file" --template "$template_file" >/dev/null; then
    echo "[lam-bridge-stack] circulation policy synced: $policy_file"
  else
    echo "[lam-bridge-stack] WARNING: circulation policy sync failed" >&2
  fi
}

stop_proc() {
  local name="$1"
  local pid_file="$PID_DIR/${name}.pid"
  if [[ ! -f "$pid_file" ]]; then
    echo "[lam-bridge-stack] $name not running"
    return 0
  fi
  local pid
  pid="$(cat "$pid_file")"
  if kill -0 "$pid" >/dev/null 2>&1; then
    kill "$pid" || true
  fi
  rm -f "$pid_file"
  echo "[lam-bridge-stack] stopped $name"
}

status_proc() {
  local name="$1"
  local pid_file="$PID_DIR/${name}.pid"
  if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" >/dev/null 2>&1; then
    echo "$name: running pid=$(cat "$pid_file")"
  else
    echo "$name: stopped"
  fi
}

case "$MODE" in
  start)
    apply_circulation_policy
    start_proc "model_worker" "$ROOT/scripts/lam_model_worker.sh" --interval-sec 5
    start_proc "portal_gateway" "$ROOT/scripts/lam_portal_gateway.sh" --mode "$PORTAL_MODE" --host 127.0.0.1 --port "$PORT"
    if [[ "$ENABLE_MCP_WATCHDOG" == "1" ]]; then
      start_proc "mcp_watchdog" "$ROOT/scripts/lam_mcp_watchdog.sh" --interval-sec 120
    fi
    if [[ "$ENABLE_GWS_BRIDGE" == "1" ]]; then
      start_proc "gws_bridge" "$ROOT/scripts/lam_gws_bridge.sh" --interval-sec 5
    fi
    if [[ "$ENABLE_SECURITY_GUARD" == "1" ]]; then
      start_proc "security_guard" "$ROOT/scripts/lam_security_telemetry_guard.sh" --interval-sec 10
    fi
    if [[ "$ENABLE_ROLE_ORCHESTRATOR" == "1" ]]; then
      start_proc "role_orchestrator" "$ROOT/scripts/lam_role_orchestrator.sh" --interval-sec 5
    fi
    if [[ "$ENABLE_POWER_FABRIC" == "1" ]]; then
      start_proc "power_fabric_guard" "$ROOT/scripts/lam_power_fabric_guard.sh" --interval-sec "${LAM_POWER_FABRIC_INTERVAL_SEC:-12}"
    fi
    if [[ "$ENABLE_REALTIME_CIRCULATION" == "1" ]]; then
      start_proc "realtime_circulation" "$ROOT/scripts/lam_realtime_circulation.sh" --daemon --interval-sec "${LAM_CIRCULATION_INTERVAL_SEC:-12}"
    fi
    if [[ "$ENABLE_DEVICE_MESH" == "1" ]]; then
      start_proc "device_mesh_daemon" "$ROOT/scripts/lam_device_mesh_daemon.sh" --interval-sec "${LAM_DEVICE_MESH_INTERVAL_SEC:-15}" --direction "${LAM_DEVICE_MESH_DIRECTION:-bidirectional}"
    fi
    if [[ "$ENABLE_ACTIVITY_TELEMETRY" == "1" ]]; then
      start_proc "activity_telemetry" "$ROOT/scripts/lam_activity_telemetry.sh" --interval-sec "${LAM_ACTIVITY_TELEMETRY_INTERVAL_SEC:-20}"
    fi
    if [[ "$ENABLE_AMBIENT_LIGHT" == "1" ]]; then
      start_proc "ambient_light" "$ROOT/scripts/lam_ambient_light.sh" --interval-sec "${LAM_AMBIENT_LIGHT_INTERVAL_SEC:-2}"
    fi
    if [[ "$ENABLE_IO_SPECTRAL" == "1" ]]; then
      start_proc "io_spectral" "$ROOT/scripts/lam_io_spectral.sh" --interval-sec "${LAM_IO_SPECTRAL_INTERVAL_SEC:-12}"
    fi
    if [[ "$ENABLE_GOVERNANCE_AUTOPILOT" == "1" ]]; then
      start_proc "governance_autopilot" "$ROOT/scripts/lam_governance_autopilot.sh" --interval-sec "${LAM_GOV_AUTOPILOT_INTERVAL_SEC:-30}"
    fi
    if [[ "$ENABLE_MEDIA_SYNC" == "1" ]]; then
      start_proc "media_sync" "$ROOT/scripts/lam_media_sync.sh" --interval-sec "${LAM_MEDIA_SYNC_INTERVAL_SEC:-6}"
    fi
    if [[ "$ENABLE_ROOTKEY_GATE" == "1" ]]; then
      start_proc "rootkey_gate" "$ROOT/scripts/lam_rootkey_gate.sh" --interval-sec "${LAM_ROOTKEY_GATE_INTERVAL_SEC:-5}"
    fi
    if [[ "$ENABLE_FAILSAFE_GUARD" == "1" ]]; then
      start_proc "failsafe_guard" "$ROOT/scripts/lam_failsafe_guard.sh" --interval-sec "${LAM_FAILSAFE_INTERVAL_SEC:-8}"
    fi
    if [[ "$ENABLE_EXTERNAL_PROVIDER_MESH" == "1" ]]; then
      start_proc "external_provider_mesh" "$ROOT/scripts/lam_external_provider_mesh.sh" --interval-sec "${LAM_EXTERNAL_PROVIDER_MESH_INTERVAL_SEC:-30}"
    fi
    if [[ "$ENABLE_FEEDBACK_GATEWAY" == "1" ]]; then
      start_proc "feedback_gateway" "$ROOT/scripts/lam_feedback_gateway.sh" --interval-sec "${LAM_FEEDBACK_GATEWAY_INTERVAL_SEC:-20}"
    fi
    if [[ "$PORTAL_MODE" == "file" ]]; then
      echo "[lam-bridge-stack] gateway=file://$ROOT/.gateway/bridge/captain"
    else
      echo "[lam-bridge-stack] gateway=http://127.0.0.1:${PORT}"
    fi
    ;;
  stop)
    stop_proc "feedback_gateway"
    stop_proc "external_provider_mesh"
    stop_proc "failsafe_guard"
    stop_proc "rootkey_gate"
    stop_proc "media_sync"
    stop_proc "governance_autopilot"
    stop_proc "io_spectral"
    stop_proc "ambient_light"
    stop_proc "activity_telemetry"
    stop_proc "device_mesh_daemon"
    stop_proc "realtime_circulation"
    stop_proc "power_fabric_guard"
    stop_proc "role_orchestrator"
    stop_proc "security_guard"
    stop_proc "gws_bridge"
    stop_proc "mcp_watchdog"
    stop_proc "portal_gateway"
    stop_proc "model_worker"
    ;;
  restart)
    "$0" stop
    "$0" start
    ;;
  status)
    status_proc "model_worker"
    status_proc "portal_gateway"
    status_proc "mcp_watchdog"
    status_proc "gws_bridge"
    status_proc "security_guard"
    status_proc "role_orchestrator"
    status_proc "power_fabric_guard"
    status_proc "realtime_circulation"
    status_proc "device_mesh_daemon"
    status_proc "activity_telemetry"
    status_proc "ambient_light"
    status_proc "io_spectral"
    status_proc "governance_autopilot"
    status_proc "media_sync"
    status_proc "rootkey_gate"
    status_proc "failsafe_guard"
    status_proc "external_provider_mesh"
    status_proc "feedback_gateway"
    ;;
  *)
    echo "usage: $0 [start|stop|restart|status]"
    exit 2
    ;;
esac
