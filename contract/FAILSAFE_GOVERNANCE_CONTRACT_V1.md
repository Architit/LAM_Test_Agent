# FAILSAFE GOVERNANCE CONTRACT V1

## Contract ID
`LAM-FAILSAFE-CONTRACT-V1`

## Objective
Guarantee deterministic containment, isolation, and rollback orchestration during P1/P2 operational instability.

## Mandatory Inputs
1. Security telemetry state (`security_telemetry_state.json`)
2. Lockdown marker (`security_lockdown.flag`)
3. Power pressure telemetry (`power_fabric_state.json`)
4. Runtime circulation policy (`routing_policy.json`)

## Mandatory Outputs
1. `failsafe_guard_state.json` with counters and policy snapshot
2. transition events (`failsafe_activated`, `failsafe_recovered`)
3. rollback request artifact (`failsafe_rollback_request.json`) while active
4. audit traces in `security_audit_stream.jsonl`

## Control Clauses
1. Containment-first:
   - if activation threshold reached, enforce fail-safe profile immediately.
2. Isolation-first:
   - data circulation kill-switch must be set to `on` during active fail-safe.
3. Rollback-ready:
   - rollback request artifact must be present during active fail-safe.
4. Recovery-gated:
   - automatic recovery only after configured stable-cycle threshold.
5. Ownership-safe cleanup:
   - fail-safe clears only overrides it created.

## SLO Gates
1. Detection-to-activation: <= `LAM_FAILSAFE_ACTIVATE_AFTER_CYCLES` guard cycles.
2. Recovery release: <= `LAM_FAILSAFE_RECOVER_AFTER_CYCLES` stable cycles (if auto-recover enabled).

## Test Evidence
- `tests/unit/test_failsafe_guard.py`
- `tests/unit/test_lam_console_core.py` (`failsafe_guard` in bridge status)

## References
- `infra/security/FAILSAFE_LIFESUPPORT_PROFILE_V1.md`
- `infra/governance/EMERGENCY_RUNBOOK.md`
- `infra/security/GATEWAY_SECURITY_PROTOCOL_V2.md`

