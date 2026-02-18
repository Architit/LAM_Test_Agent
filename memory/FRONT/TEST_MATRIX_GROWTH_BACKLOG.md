# TEST_MATRIX_GROWTH_BACKLOG

Generated: 2026-02-17 21:31 UTC

## Safety Guardrails
- Deterministic generation order only.
- Hard caps active: max tasks and per-route limit.
- No recursive self-expansion; generator outputs one backlog artifact only.

## Snapshot Summary
- routes_total: 9
- unique_route_ids: 8
- live_ready: False

## Backlog Items
- [P0] R-001 / scn_codex_comm_ping_pong: Enable live route test for R-001 (comm-agent -> codex-agent)
  Acceptance: Live mode executes scenario route with real submodule agents and preserves trace continuity.
- [P0] R-002 / scn_codex_comm_ping_pong: Enable live route test for R-002 (codex-core -> comm-agent)
  Acceptance: Live mode executes scenario route with real submodule agents and preserves trace continuity.
- [P0] R-003 / scn_comm_roaudter_fallback: Enable live route test for R-003 (comm-agent -> roaudter-agent)
  Acceptance: Live mode executes scenario route with real submodule agents and preserves trace continuity.
- [P0] R-004 / scn_comm_roaudter_fallback: Enable live route test for R-004 (roaudter-agent -> provider-router-core)
  Acceptance: Live mode executes scenario route with real submodule agents and preserves trace continuity.
- [P0] R-005 / scn_comm_roaudter_fallback: Enable live route test for R-005 (provider-router-core -> local-provider)
  Acceptance: Live mode executes scenario route with real submodule agents and preserves trace continuity.
- [P0] R-006 / scn_taskarid_chain_route: Enable live route test for R-006 (taskarid-core -> comm-agent)
  Acceptance: Live mode executes scenario route with real submodule agents and preserves trace continuity.
- [P0] R-007 / scn_taskarid_chain_route: Enable live route test for R-007 (codex-agent -> comm-agent)
  Acceptance: Live mode executes scenario route with real submodule agents and preserves trace continuity.
- [P0] R-007 / scn_taskarid_chain_route: Enable live route test for R-007 (comm-agent -> codex-agent)
  Acceptance: Live mode executes scenario route with real submodule agents and preserves trace continuity.
- [P0] R-008 / scn_taskarid_chain_route: Enable live route test for R-008 (comm-agent -> roaudter-agent)
  Acceptance: Live mode executes scenario route with real submodule agents and preserves trace continuity.
