# POWER SYNC AND QUIET PROTOCOL V1

## Scope
Global orchestration for CPU/GPU/RAM/swap/I/O load windows, wake states, turbo peaks, and quiet-cooling periods.

## Design Intent
- Full-capacity operation during active windows.
- Controlled cooling/noise reduction during quiet windows ("night mode").
- Deterministic telemetry and auditable policy decisions.

## Runtime Guard
- Component: `power_fabric_guard`
- Entry points:
  - `scripts/lam_power_fabric_guard.sh --once`
  - `scripts/lam_power_fabric_guard.sh --interval-sec 12`
- State outputs:
  - `LAM_HUB_ROOT/power_fabric_state.json`
  - `LAM_HUB_ROOT/noise_guard.flag` (only when quiet-hours noise policy is violated)
  - `LAM_HUB_ROOT/power_profile.override` (manual profile control plane)

## Telemetry Surface
- CPU: `load1/load5/load15`, `load_ratio` normalized by CPU count.
- RAM: `MemAvailable`.
- Swap/pagefile (Linux swap): total, used MB, used percent.
- I/O pressure: iowait percent proxy from `/proc/stat`.
- GPU: `nvidia-smi` utilization/memory/temp when available.
- Noise proxy: max fan RPM from `/sys/class/hwmon`.

## Modes
- `turbo_peak`:
  - high load ratio, swap pressure, iowait pressure, or high GPU utilization.
- `balanced`:
  - normal operation window.
- `quiet_cooling`:
  - quiet-hours active; prioritize low-noise cooling behavior.

## Key Policy Controls
- `LAM_QUIET_HOURS_START=22`
- `LAM_QUIET_HOURS_END=7`
- `LAM_QUIET_FAN_RPM_MAX=2200`
- `LAM_ENFORCE_NOISE_GUARD=1`
- `LAM_TURBO_LOAD_RATIO=0.85`
- `LAM_TURBO_SWAP_USED_PCT=25`
- `LAM_TURBO_IOWAIT_PCT=12`

## Boot-Level Integration Contract
Direct firmware logic changes are out of repo scope.
Supported "hardware-close" path is:
1. BIOS/UEFI config (fan curves, power plans, Secure Boot, thermal policies).
2. Early OS services:
   - `lam-boot-integrity.service`
   - `lam-security-telemetry.service`
   - `lam-power-fabric.service`
3. Control-plane orchestration after gates are active.

This keeps policy enforcement near startup rather than late in user-space apps.

## Safety Rules
- Quiet hours do not disable critical safety controls.
- Any persistent noise violation in quiet hours raises `noise_guard.flag`.
- Security lockdown has higher priority than turbo mode.

## Operational Commands
```bash
scripts/lam_power_fabric_guard.sh --once
scripts/power_profilectl.sh status
scripts/power_profilectl.sh set turbo
scripts/power_profilectl.sh set quiet
scripts/power_profilectl.sh set auto
scripts/power_profilectl.sh clear
scripts/lam_bridge_stack.sh status
```

## Root-Only System Layer
- System-wide profile propagation is restricted to root-level operator control.
- Commands:
```bash
sudo scripts/power_profilectl.sh set quiet --system
sudo scripts/power_profilectl.sh clear --system
```
- System profile is stored in `/etc/default/lam-control-plane` as `LAM_POWER_PROFILE_OVERRIDE`.
