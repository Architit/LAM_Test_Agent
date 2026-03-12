# Role Orchestration Protocol V1

## Purpose
Realtime role control for AI agents immediately after device wake/resume.

## Runtime Components
- `role_orchestrator` daemon
- `security_guard`
- `mcp_watchdog`
- `gws_bridge`
- role profiles: `infra/security/role_profiles.json`
- profile selector: `infra/security/role_selector.json`
- runtime override: `LAM_HUB_ROOT/role_profile.override`

## Wake Trigger
A wake event is detected when monotonic time gap exceeds `LAM_WAKE_DETECT_THRESHOLD_SEC`.

## Mandatory Wake Actions
1. Rebind critical roles (`captain`, `security_sentinel`, `memory_archivist`, `model_dispatcher`).
2. Emit wake event to bridge logs.
3. Trigger storage/queue revalidation (`gws health`, `sync_pull`, `run_queue`).
4. Refresh bridge status and publish orchestration state.

## Dynamic Profile Switching
- Runtime may switch profile based on hardware/resource telemetry:
  - battery mode -> `edge_gateway`
  - high load -> `edge_gateway`
  - thermal stress -> `edge_gateway` or `critical_lifeline_degraded`
- Reason codes are emitted in wake event payload.

## Safety Constraints
- If `security_lockdown.flag` is present, privileged orchestration remains blocked by control-plane supervisor.
- Role rebinding cannot bypass security guard policy.
- Under lockdown, wake event is logged but role rebind fanout is suppressed.
- With `LAM_WAKE_STRICT_SECURE_GATE=1`, wake actions are blocked unless secure posture is valid.
- Repeated critical reason-codes activate orchestration hold runbook (`role_orchestrator_hold.flag`).

## Observability
- `LAM_HUB_ROOT/role_orchestrator_state.json`
- `LAM_HUB_ROOT/role_orchestrator_counters.json`
- `LAM_HUB_ROOT/role_orchestrator_hold.flag`
- `LAM_HUB_ROOT/security_audit_stream.jsonl`
- `LAM_CAPTAIN_BRIDGE_ROOT/wake_events.jsonl`
- `LAM_CAPTAIN_BRIDGE_ROOT/events.jsonl`
