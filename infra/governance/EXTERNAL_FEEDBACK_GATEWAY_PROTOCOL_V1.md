# EXTERNAL FEEDBACK GATEWAY PROTOCOL V1

## Purpose
Autopilot feedback/recommendation delivery into external gateways/channels with controlled dispatch and spool fallback.

## Runtime Service
- daemon: `scripts/lam_feedback_gateway.sh --interval-sec 20`
- stack process: `feedback_gateway`

## Inputs
1. External provider readiness:
- `LAM_HUB_ROOT/external_provider_mesh_state.json`

2. Autopilot state sources:
- `LAM_HUB_ROOT/governance_autopilot_state.json`
- `LAM_HUB_ROOT/security_telemetry_state.json`
- `LAM_HUB_ROOT/failsafe_guard_state.json`
- `LAM_HUB_ROOT/power_fabric_state.json`

3. Manual feedback queue:
- `LAM_CAPTAIN_BRIDGE_ROOT/feedback_requests.jsonl`

## Outputs
1. Provider outboxes:
- `LAM_CAPTAIN_BRIDGE_ROOT/external_feedback/<provider>.jsonl`

2. Dispatch receipts:
- `LAM_CAPTAIN_BRIDGE_ROOT/feedback_dispatch_receipts.jsonl`

3. Undelivered spool:
- `LAM_HUB_ROOT/feedback_dispatch_spool.jsonl`

4. Runtime state:
- `LAM_HUB_ROOT/feedback_gateway_state.json`

## Dispatch Rules
1. Target only channels marked `ready=true` by external mesh.
2. If no ready targets for an item, write to spool.
3. Safety gate:
- if `security_lockdown.flag` or `failsafe_active.flag` exists, non-critical feedback is blocked to spool.
- critical feedback is limited to `LAM_FEEDBACK_CRITICAL_ALLOWED` channels.
4. Emit cycle event + audit trail each tick.

## Signals
- `sent_count`
- `spooled_count`
- `feedback_pressure`
- `status` (`ok|degraded`)
