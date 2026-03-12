# FAILSAFE LIFESUPPORT PROFILE V1

## Purpose
Define a software-level fail-safe profile for critical ecosystem continuity when telemetry crosses emergency thresholds.

## Runtime Component
- daemon: `scripts/lam_failsafe_guard.sh --interval-sec 8`
- state file: `LAM_HUB_ROOT/failsafe_guard_state.json`
- activation flag: `LAM_HUB_ROOT/failsafe_active.flag`

## Activation Inputs
1. `security_telemetry_state.json` shows `overall_ok=false`
2. `security_lockdown.flag` is present
3. force trigger file exists: `LAM_HUB_ROOT/failsafe_force.flag`
4. critical pressure metrics:
   - `load_ratio >= LAM_FAILSAFE_MAX_LOAD_RATIO`
   - `swap_used_pct >= LAM_FAILSAFE_MAX_SWAP_USED_PCT`
   - `iowait_pct >= LAM_FAILSAFE_MAX_IOWAIT_PCT`
   - `gpu_temp_c >= LAM_FAILSAFE_MAX_GPU_TEMP_C`

Activation threshold:
- `LAM_FAILSAFE_ACTIVATE_AFTER_CYCLES` consecutive critical cycles.

## Containment Actions
1. Enforce role profile override:
   - `LAM_HUB_ROOT/role_profile.override = LAM_FAILSAFE_ROLE_PROFILE`
2. Enforce power profile override:
   - `LAM_HUB_ROOT/power_profile.override = LAM_FAILSAFE_POWER_PROFILE`
3. Activate circulation kill-switch in routing policy:
   - `data_circulation.kill_switch=true`
4. Activate orchestration hold:
   - `LAM_HUB_ROOT/role_orchestrator_hold.flag`
5. Write rollback request:
   - `LAM_HUB_ROOT/failsafe_rollback_request.json`
6. Ensure security lockdown marker exists.

## Recovery / Rollback
- If `LAM_FAILSAFE_AUTO_RECOVER=1`, guard exits fail-safe after
  `LAM_FAILSAFE_RECOVER_AFTER_CYCLES` stable cycles.
- On recovery:
  - clears fail-safe active flag and rollback request
  - releases overrides owned by fail-safe
  - disables circulation kill-switch if fail-safe enabled it

## Audit Requirements
- Every cycle writes `failsafe_cycle` event to:
  - `LAM_CAPTAIN_BRIDGE_ROOT/events.jsonl`
  - `LAM_HUB_ROOT/security_audit_stream.jsonl`
- transitions emit:
  - `failsafe_activated`
  - `failsafe_recovered`

## Scope Boundary
This profile is software/orchestration only and does not perform direct BIOS/firmware control.

