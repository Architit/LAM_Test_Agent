#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYSTEMD_TPL_DIR="$ROOT/deploy/systemd"

RUN_USER="${SUDO_USER:-${USER:-}}"
REPO_ROOT="$ROOT"
ENABLE_TTY=1
INSTALL_DEPS=0
STATE_ROOT_BASE="${LAM_STATE_ROOT_BASE:-/var/lib/lam-runtime}"
ENV_FILE="/etc/default/lam-control-plane"

usage() {
  cat <<'EOF'
Usage:
  sudo scripts/autonomous_bootstrap.sh full [--repo-root PATH] [--user NAME] [--no-tty] [--install-deps]
  sudo scripts/autonomous_bootstrap.sh install-services [--repo-root PATH] [--user NAME] [--no-tty]
  sudo scripts/autonomous_bootstrap.sh enable
  sudo scripts/autonomous_bootstrap.sh status
  sudo scripts/autonomous_bootstrap.sh disable

Notes:
  - Designed for native Linux + systemd (not WSL).
  - Installs system services for control-plane worker and optional tty1 Captain Bridge console.
EOF
}

die() {
  echo "[autonomous-bootstrap] $*" >&2
  exit 1
}

require_root() {
  [[ "${EUID}" -eq 0 ]] || die "run as root (sudo)."
}

check_native_linux() {
  [[ -d /run/systemd/system ]] || die "systemd runtime not detected."
  if ! systemctl list-unit-files >/dev/null 2>&1; then
    die "systemd is present but not reachable as PID1/bus. Run on native Linux boot, not WSL/container shell."
  fi
  if grep -qiE 'microsoft|wsl' /proc/version 2>/dev/null; then
    die "WSL detected; this script targets autonomous native Linux only."
  fi
}

render_tpl() {
  local tpl="$1"
  local out="$2"
  sed \
    -e "s#{{RUN_USER}}#${RUN_USER}#g" \
    -e "s#{{REPO_ROOT}}#${REPO_ROOT}#g" \
    "$tpl" > "$out"
}

repo_slug() {
  basename "$REPO_ROOT" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9._-' '_'
}

render_runtime_env() {
  local slug state_root
  slug="$(repo_slug)"
  state_root="${STATE_ROOT_BASE}/${slug}"

  install -d -o "$RUN_USER" -g "$RUN_USER" "$state_root"
  install -d -o "$RUN_USER" -g "$RUN_USER" "$state_root/gateway"
  install -d -o "$RUN_USER" -g "$RUN_USER" "$state_root/hub"
  install -d -o "$RUN_USER" -g "$RUN_USER" "$state_root/bridge/captain"
  install -d -o "$RUN_USER" -g "$RUN_USER" "$state_root/exchange/gws"
  install -d -o "$RUN_USER" -g "$RUN_USER" "$state_root/stack/pids"
  install -d -o "$RUN_USER" -g "$RUN_USER" "$state_root/stack/logs"
  install -d -o "$RUN_USER" -g "$RUN_USER" "$state_root/security"

  cat > "$ENV_FILE" <<EOF
LAM_STATE_ROOT=$state_root
LAM_GATEWAY_STATE_DIR=$state_root/gateway
LAM_HUB_ROOT=$state_root/hub
LAM_CAPTAIN_BRIDGE_ROOT=$state_root/bridge/captain
LAM_GWS_LOCAL_DIR=$state_root/exchange/gws
LAM_STACK_PID_DIR=$state_root/stack/pids
LAM_STACK_LOG_DIR=$state_root/stack/logs
LAM_PORTAL_MODE=file
LAM_ENABLE_MCP_WATCHDOG=1
LAM_ENABLE_GWS_BRIDGE=1
LAM_ENABLE_SECURITY_GUARD=1
LAM_ENABLE_ROLE_ORCHESTRATOR=1
LAM_ENABLE_POWER_FABRIC=1
LAM_ENABLE_REALTIME_CIRCULATION=1
LAM_ENABLE_DEVICE_MESH=1
LAM_ENABLE_ACTIVITY_TELEMETRY=1
LAM_ENABLE_IO_SPECTRAL=1
LAM_ENABLE_GOVERNANCE_AUTOPILOT=1
LAM_ENABLE_MEDIA_SYNC=1
LAM_ENABLE_ROOTKEY_GATE=1
LAM_ENABLE_HMAC_ROTATION=1
LAM_ENABLE_FAILSAFE_GUARD=1
LAM_ENABLE_EXTERNAL_PROVIDER_MESH=1
LAM_ENABLE_FEEDBACK_GATEWAY=1
LAM_ROOTKEY_GATE_INTERVAL_SEC=5
LAM_ROOTKEY_ENABLE=1
LAM_ROOTKEY_MEDIA_ROOT=$state_root/exchange/removable
LAM_ROOTKEY_FILE_REL=.radriloniuma/rootkey/architit_root.key
LAM_ROOTKEY_RESPONSE_FILE_REL=.radriloniuma/rootkey/challenge_response.sha256
LAM_ROOTKEY_REQUIRE_CHALLENGE=1
LAM_ROOTKEY_CHALLENGE_TTL_SEC=180
LAM_ROOTKEY_CHALLENGE_AUTO_ROTATE_SEC=60
LAM_ROOTKEY_FAIL_THRESHOLD=3
LAM_ROOTKEY_BAN_SEC=300
# Recommended: set expected SHA256 digest of key payload.
# LAM_ROOTKEY_ARCHITIT_SHA256=<sha256>
LAM_MEDIA_SYNC_MODE=bidirectional
LAM_MEDIA_SYNC_INTERVAL_SEC=6
LAM_MEDIA_SYNC_MAX_OPS_PER_TICK=32
LAM_MEDIA_SYNC_MAX_SCAN_FILES=8000
LAM_MEDIA_SYNC_CLASS_ORDER=instructions,contracts,protocols,policies,licenses,map,cards,keypass_code_dnagen,other
LAM_MEDIA_SYNC_CLASS_MAX_OPS=instructions:16,contracts:12,protocols:10,policies:8,licenses:8,map:6,cards:6,keypass_code_dnagen:4,other:4
LAM_MEDIA_DEVICE_ROOT=$state_root/exchange/device
LAM_MEDIA_REMOVABLE_ROOT=$state_root/exchange/removable
LAM_CIRCULATION_REQUIRE_CRYPTO_MIRROR=1
LAM_CIRCULATION_HMAC_KEY_FILE=$state_root/security/circulation_hmac.key
LAM_CIRCULATION_HMAC_SECONDARY_KEY_FILE=$state_root/security/circulation_hmac_prev.key
LAM_CIRCULATION_HMAC_ROTATION_STATE_FILE=$state_root/security/circulation_hmac_rotation.json
LAM_CIRCULATION_HMAC_SECONDARY_GRACE_SEC=86400
LAM_CIRCULATION_HMAC_ROTATE_INTERVAL_SEC=86400
LAM_CIRCULATION_HMAC_KEY_ID=rootkey-mirror-v1
LAM_FAILSAFE_INTERVAL_SEC=8
LAM_FAILSAFE_ACTIVATE_AFTER_CYCLES=2
LAM_FAILSAFE_RECOVER_AFTER_CYCLES=5
LAM_FAILSAFE_AUTO_RECOVER=1
LAM_FAILSAFE_ROLE_PROFILE=critical_lifeline
LAM_FAILSAFE_POWER_PROFILE=quiet
LAM_FAILSAFE_MAX_LOAD_RATIO=0.95
LAM_FAILSAFE_MAX_SWAP_USED_PCT=60
LAM_FAILSAFE_MAX_IOWAIT_PCT=25
LAM_FAILSAFE_MAX_GPU_TEMP_C=90
LAM_EXTERNAL_PROVIDER_MESH_INTERVAL_SEC=30
LAM_FEEDBACK_GATEWAY_INTERVAL_SEC=20
LAM_MCP_AUTO_HEAL=1
LAM_SECURITY_ENFORCE=1
LAM_SECURITY_MIN_DISK_GB=5
LAM_SECURITY_MIN_MEM_MB=512
LAM_SECURITY_MAX_LOAD=32
LAM_POWER_FABRIC_INTERVAL_SEC=12
LAM_QUIET_HOURS_START=22
LAM_QUIET_HOURS_END=7
LAM_QUIET_FAN_RPM_MAX=2200
LAM_ENFORCE_NOISE_GUARD=1
LAM_TURBO_LOAD_RATIO=0.85
LAM_TURBO_SWAP_USED_PCT=25
LAM_TURBO_IOWAIT_PCT=12
LAM_DEVICE_MESH_INTERVAL_SEC=15
LAM_DEVICE_MESH_DIRECTION=bidirectional
LAM_ACTIVITY_TELEMETRY_INTERVAL_SEC=20
# Set to 1 for strict Secure Boot enforcement on supported hardware:
LAM_BOOT_REQUIRE_SECURE_BOOT=0
LAM_SECURITY_REQUIRE_SECURE_BOOT=0
# Optional path to local Google Drive mirror:
# LAM_GWS_DRIVE_ROOT=/path/to/GoogleDrive
EOF
  chmod 0644 "$ENV_FILE"
}

install_deps() {
  if [[ "$INSTALL_DEPS" != "1" ]]; then
    return 0
  fi
  if command -v apt-get >/dev/null 2>&1; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y python3 python3-venv python3-pip rsync curl git
  else
    echo "[autonomous-bootstrap] package manager not supported automatically; install deps manually." >&2
  fi
}

install_services() {
  require_root
  check_native_linux
  [[ -n "$RUN_USER" ]] || die "unable to resolve run user; pass --user."

  mkdir -p /etc/systemd/system
  render_runtime_env
  render_tpl "$SYSTEMD_TPL_DIR/lam-boot-integrity.service.tpl" /etc/systemd/system/lam-boot-integrity.service
  render_tpl "$SYSTEMD_TPL_DIR/lam-security-telemetry.service.tpl" /etc/systemd/system/lam-security-telemetry.service
  render_tpl "$SYSTEMD_TPL_DIR/lam-power-fabric.service.tpl" /etc/systemd/system/lam-power-fabric.service
  render_tpl "$SYSTEMD_TPL_DIR/lam-hmac-rotation.service.tpl" /etc/systemd/system/lam-hmac-rotation.service
  render_tpl "$SYSTEMD_TPL_DIR/lam-control-plane.service.tpl" /etc/systemd/system/lam-control-plane.service
  if [[ "$ENABLE_TTY" == "1" ]]; then
    render_tpl "$SYSTEMD_TPL_DIR/lam-captain-tty.service.tpl" /etc/systemd/system/lam-captain-tty.service
  else
    rm -f /etc/systemd/system/lam-captain-tty.service || true
  fi
  systemctl daemon-reload
}

wait_service_active() {
  local unit="$1"
  local timeout_sec="${2:-30}"
  local i=0
  while (( i < timeout_sec )); do
    if systemctl is-active --quiet "$unit"; then
      return 0
    fi
    sleep 1
    i=$((i + 1))
  done
  return 1
}

enable_services() {
  require_root
  systemctl enable lam-boot-integrity.service
  systemctl restart lam-boot-integrity.service
  systemctl enable lam-security-telemetry.service
  systemctl restart lam-security-telemetry.service
  systemctl enable lam-power-fabric.service
  systemctl restart lam-power-fabric.service
  systemctl enable lam-hmac-rotation.service
  systemctl restart lam-hmac-rotation.service
  wait_service_active lam-hmac-rotation.service 30 || die "lam-hmac-rotation.service failed to become active"
  systemctl enable lam-control-plane.service
  systemctl restart lam-control-plane.service
  wait_service_active lam-control-plane.service 45 || die "lam-control-plane.service failed to become active"
  if [[ -f /etc/systemd/system/lam-captain-tty.service ]]; then
    systemctl enable lam-captain-tty.service
    systemctl restart lam-captain-tty.service
    wait_service_active lam-captain-tty.service 30 || die "lam-captain-tty.service failed to become active"
  fi
}

disable_services() {
  require_root
  systemctl disable --now lam-captain-tty.service 2>/dev/null || true
  systemctl disable --now lam-control-plane.service 2>/dev/null || true
  systemctl disable --now lam-hmac-rotation.service 2>/dev/null || true
  systemctl disable --now lam-power-fabric.service 2>/dev/null || true
  systemctl disable --now lam-security-telemetry.service 2>/dev/null || true
  systemctl disable --now lam-boot-integrity.service 2>/dev/null || true
}

status_services() {
  check_native_linux
  local rc=0
  systemctl --no-pager --full status lam-boot-integrity.service || true
  systemctl is-active --quiet lam-boot-integrity.service || rc=1
  systemctl --no-pager --full status lam-security-telemetry.service || true
  systemctl is-active --quiet lam-security-telemetry.service || rc=1
  systemctl --no-pager --full status lam-power-fabric.service || true
  systemctl is-active --quiet lam-power-fabric.service || rc=1
  systemctl --no-pager --full status lam-hmac-rotation.service || true
  systemctl is-active --quiet lam-hmac-rotation.service || rc=1
  systemctl --no-pager --full status lam-control-plane.service || true
  systemctl is-active --quiet lam-control-plane.service || rc=1
  systemctl --no-pager --full status lam-captain-tty.service || true
  if [[ -f /etc/systemd/system/lam-captain-tty.service ]]; then
    systemctl is-active --quiet lam-captain-tty.service || rc=1
  fi
  return "$rc"
}

CMD="${1:-}"
shift || true

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-root)
      REPO_ROOT="$2"; shift 2;;
    --user)
      RUN_USER="$2"; shift 2;;
    --no-tty)
      ENABLE_TTY=0; shift;;
    --install-deps)
      INSTALL_DEPS=1; shift;;
    -h|--help)
      usage; exit 0;;
    *)
      die "unknown arg: $1";;
  esac
done

case "$CMD" in
  full)
    check_native_linux
    install_deps
    install_services
    enable_services
    status_services
    ;;
  install-services)
    install_services
    ;;
  enable)
    enable_services
    ;;
  disable)
    disable_services
    ;;
  status)
    status_services
    ;;
  *)
    usage
    exit 2
    ;;
esac
