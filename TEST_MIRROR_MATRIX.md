# TEST_MIRROR_MATRIX — LAM_Test_Agent

## Route Matrix (Agent/Core/Ecosystem Levels)

| Route ID | Producer | Consumer | Layer Pair | Required Test Families | Current Status |
|---|---|---|---|---|---|
| R-001 | comm-agent | codex-agent | agent -> agent | payload schema, ping reply envelope, trace continuity | active |
| R-002 | codex-core | comm-agent | core -> agent | response normalization, status invariants | active |
| R-003 | comm-agent | roaudter-agent | agent -> agent | provider hint handling, fallback determinism, usage fields | active |
| R-004 | roaudter-agent | provider-router-core | agent -> core | routing policy compliance, degrade behavior | active |
| R-005 | provider-router-core | local-provider | core -> ecosystem | local fallback eligibility and result envelope | active |
| R-006 | taskarid-core | comm-agent | core -> agent | task envelope integrity, trace propagation | active |
| R-007 | comm-agent | codex-agent | agent -> agent | roundtrip compatibility under task chain | active |
| R-008 | comm-agent | roaudter-agent | agent -> agent | chain completion and final response contract | active |

## Mirror Search Targets
- Interface mirror: missing field assertions on producer/consumer boundaries.
- Behavior mirror: same failure input should trigger equivalent degradation mode.
- Operational mirror: startup/test-entrypoint compatibility in route participants.
- Governance mirror: roadmap/contract claims must map to executable tests.

## Priority Labels
- `P0`: route break causes ecosystem stop.
- `P1`: route drift causes degraded but recoverable behavior.
- `P2`: local inconsistency with low blast radius.
