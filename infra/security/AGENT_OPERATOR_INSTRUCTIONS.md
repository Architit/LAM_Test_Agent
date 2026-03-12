# Agent & Operator Instructions (Security)

## Default Mode
Agents must start in `guest-gateway` unless user explicitly approves higher access.

## Escalation
Escalate to `install` only when:
1. user confirms persistence intent,
2. rollback path is available,
3. telemetry guard is healthy.

## Prohibited Behavior
- No silent persistence without explicit approved policy.
- No bypass of boot integrity checks.
- No disabling telemetry guard in production profile.

## Recovery Path
- Run `revoke` mode to stop stack and remove scheduled autopilot.
- Inspect logs in `ProgramData\\RADRILONIUMA\\logs` (Windows) or runtime state root (Linux).
- For fail-safe incidents:
  - inspect `LAM_HUB_ROOT/failsafe_guard_state.json`
  - inspect `LAM_HUB_ROOT/failsafe_rollback_request.json`
  - verify `data_circulation.kill_switch` state before resuming cross-node sync

## AI Agent Safety Notes
- Any action that changes persistence must be announced with intended impact.
- If security lock flag is present, agents must halt privileged actions.
- Licensing gate is mandatory before release/publish:
  - run `scripts/license_audit_scan.sh`
  - run `scripts/license_change_guard.sh --mode verify`
  - if any repo has `missing_license` or `unknown_license_type`, release actions must stop
  - if guard reports license change without approval, release actions must stop
  - attach latest `infra/governance/LICENSE_AUDIT_REPORT_<date>.md` to operator report
- Fail-safe policy:
  - when `failsafe_active.flag` exists, agents must avoid non-essential writes and treat routing as degraded.
  - resume normal routing only after explicit recovery evidence (`stable_cycles` threshold reached or operator override).
