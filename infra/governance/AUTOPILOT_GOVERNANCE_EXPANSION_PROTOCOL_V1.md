# AUTOPILOT GOVERNANCE EXPANSION PROTOCOL V1

## Scope
Expands autopilot rights and runtime controls across:
- protocoling
- planning
- analyzing
- strategizing
- contracting
- politizing (policy governance)
- instructing
- revising
- licensing
- mapping
- topologizing
- chronologizing

## Runtime
- daemon: `scripts/lam_governance_autopilot.sh --interval-sec 30`
- one-shot: `scripts/lam_governance_autopilot.sh --once`

## State
- `LAM_HUB_ROOT/governance_autopilot_state.json`
- `LAM_HUB_ROOT/governance_autopilot_timeline.jsonl`

## Signals
- `autopilot_status`: `ok|degraded`
- `governance_pressure`: ratio of degraded domains
- `domains_degraded`, `domains_ok`, `domains_total`

## Corrective Vectors
Autopilot emits per-domain corrective vectors:
- `materialize_missing_artifacts` (P1)
- `refresh_stale_artifacts` (P2)
- `none` (P3)

## Guardrail
Autopilot does not mutate legal/license files directly.
For licensing, it only points to compliance workflows:
- `scripts/license_audit_scan.sh`
- `scripts/license_change_guard.sh --mode verify`
