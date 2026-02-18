# TEST_MATRIX_EXPANSION_EXEC_PLAN — FRONT (2026-02-17)

Status: IN_PROGRESS (Wave 1-5 delivered)

## Objective
Expand executable route-matrix coverage in `LAM_Test_Agent` from single integration path to a scenario-driven matrix with contract assertions.

## Waves
1. Wave 0 (blockers)
- Restore submodule-ready checks and prevent false-green integration status when sources are absent.

2. Wave 1 (execution backbone)
- Add scenario-driven route execution backbone.
- Add integration tests that execute every registered scenario through deterministic test doubles.

3. Wave 2 (contract assertions)
- Enforce status, trace continuity, fallback semantics, and envelope invariants per route family.

4. Wave 3 (failure topology)
- Add mirrored failure-mode tests for provider outage, malformed envelope, missing required fields.

5. Wave 4 (CI hardening)
- Split runtime coverage from tests coverage.
- Raise minimum coverage gate in steps.

## Target KPIs
- Integration tests: 1 -> >= 12
- Route ID coverage: R-001..R-008 = 100%
- Negative tests: >= 2 per route
- Runtime-only coverage gate: >= 60% (first raise)

## Execution log
- 2026-02-17: Plan persisted into FRONT memory layer.
- 2026-02-17: Wave 1 implementation started (scenario-driven route matrix tests).
- 2026-02-17: Added route matrix executor (`lam_test_agent_route_matrix.py`) and integration suite (`tests/it/test_route_matrix_mock.py`).
- 2026-02-17: Route coverage baseline verified for `R-001..R-008` via scenario registry.
- 2026-02-17: Added contract envelope normalization and roundtrip checks for route execution payloads.
- 2026-02-17: Added negative-path integration checks for invalid route envelopes and provider outage degradation behavior.
- 2026-02-17: Added failure-topology invariant validator for route execution results.
- 2026-02-17: Added failure tests for trace break, degraded-without-fallback, and provider-unavailable status mismatch.
- 2026-02-17: Test scale after Wave 3 partial: 88 collected, 87 passed, 1 skipped.
- 2026-02-17: CI split into `quality`, `unit-runtime-cov`, `integration` jobs.
- 2026-02-17: Runtime-only coverage gate enabled at 60% (current local: 60.32% on unit-only run).
- 2026-02-17: Added matrix sync guard (`TEST_MIRROR_MATRIX.md` route IDs vs code mapping).
- 2026-02-17: Added unit coverage for route-matrix core paths; runtime-only coverage gate raised to 65%.
- 2026-02-17: Current unit-runtime coverage result: 88.66% (threshold 65%).
- 2026-02-17: Added advanced matrix-status guard (`active/planned` consistency with route coverage state).
- 2026-02-17: Route matrix statuses synchronized to active for `R-001..R-008`.
- 2026-02-17: Current test scale: 98 collected, 97 passed, 1 skipped.
- 2026-02-17: Added anti-deadloop plan guard (`lam_test_agent_plan_guard.py`) and CI enforcement in `quality` job.
- 2026-02-17: Current test scale: 103 collected, 102 passed, 1 skipped.
- 2026-02-17: Deadloop guard expanded to ecosystem-wide markdown scan (`--ecosystem`), with global repeating-window cycle detection (window sizes 1..5, not tail-only).
- 2026-02-17: Current test scale: 106 collected, 105 passed, 1 skipped.
- 2026-02-17: Added growth data collector (`lam_test_agent_growth_data.py`) for route-level gap telemetry (`mock/contract/failure/live`).
- 2026-02-17: Growth snapshot persisted in FRONT memory: `memory/FRONT/TEST_MATRIX_GROWTH_SNAPSHOT.json`.
- 2026-02-17: Current test scale: 109 collected, 108 passed, 1 skipped.
- 2026-02-17: Added bounded growth backlog generator (`lam_test_agent_growth_backlog.py`) with hard caps and no-recursion guardrails.
- 2026-02-17: Growth backlog persisted in FRONT memory: `memory/FRONT/TEST_MATRIX_GROWTH_BACKLOG.md`.
- 2026-02-17: Current test scale: 114 collected, 113 passed, 1 skipped.
- 2026-02-17: WB-02 started — ecosystem protocol expansion strategy published and integrated into governance artifacts.
- 2026-02-17: Added machine-readable ecosystem safety/resource stack and CI gate validation (`lam_test_agent_safety_stack.py`).
- 2026-02-17: Current test scale: 117 collected, 116 passed, 1 skipped.
- 2026-02-17: Pre-Phase-E live baseline collected via ecosystem telemetry (`lam_test_agent_ecosystem_telemetry.py`).
- 2026-02-17: Telemetry snapshot persisted: `memory/FRONT/ECOSYSTEM_TELEMETRY_SNAPSHOT_2026-02-17.{json,md}`.
- 2026-02-17: Current test scale: 120 collected, 119 passed, 1 skipped.
- 2026-02-17: Phase E live activation policy checks added (`lam_test_agent_live_policy.py`) and wired to telemetry + growth readiness gates.
- 2026-02-17: Live policy artifacts persisted: `memory/FRONT/LIVE_ACTIVATION_POLICY_REPORT_2026-02-17.{json,md}` (current status: `BLOCKED`, mode=`mock_only`).
- 2026-02-17: Current test scale: 122 collected, 121 passed, 1 skipped.
- 2026-02-17: Phase E drift report added (`lam_test_agent_phasee_drift.py`) with stack-vs-implementation coverage and unblock conditions.
- 2026-02-17: Drift artifacts persisted: `memory/FRONT/PHASE_E_DRIFT_REPORT_2026-02-17.{json,md}` (coverage=96.15%, missing_layers=1).
- 2026-02-17: Current test scale: 124 collected, 123 passed, 1 skipped.
- 2026-02-17: Degraded-mode conformance wired into live policy gate; Phase E drift now `coverage=100.0%` and `missing_layers=0`.
- 2026-02-17: Current test scale: 125 collected, 124 passed, 1 skipped.
- 2026-02-18: Semantic subtree healing finalized for `ARGD/Arrierguard`; physical root materialized in `Archivator_Agent/SubtreeHub`.
- 2026-02-18: Live policy status recovered to `READY` (`live_plus_mock`), critical gates green.
- 2026-02-18: Archivator refresh completed (`global_refresh:ok`), and `ARGD/Arrierguard` presence confirmed in `ecosystem_file_matrix_latest.tsv`.
