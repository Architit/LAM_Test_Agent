# WB-01 — LAM_Test_Agent Deep Analysis, Development, Growth, Evolution, Expansion Plan (2026-02-17)

## 1. Executive Summary
- Repository role: integration validation harness for multi-agent interaction (`codex-agent` + `comm-agent`) through ping-pong scenarios.
- Current maturity: governance docs are present; engineering surface is minimal and partially blocked by submodule dependency state.
- Primary blocker: submodules are not initialized in local workspace, causing import failures in integration tests.

## 2. Source Basis (Maps / Plans / Logs / Contracts)
- `ROADMAP.md`
- `DEV_LOGS.md`
- `WORKFLOW_SNAPSHOT_STATE.md`
- `INTERACTION_PROTOCOL.md`
- `.github/workflows/main.yml`
- `tests/it/ping_pong_test.py`
- `scripts/ping_pong_test.py`
- `.gitmodules`

## 3. Repository Architecture Map (Current)

### 3.1 Test Surface
- `tests/test_runtime_smoke.py`: placeholder smoke test (`assert True`).
- `tests/it/ping_pong_test.py`: integration path using submodule-provided agent packages.
- `scripts/ping_pong_test.py`: near-duplicate executable scenario for manual check.

### 3.2 Dependency Topology
- Submodule `LAM_Test/agents/codex-agent`
- Submodule `LAM_Test/agents/comm-agent`
- `requirements-dev.txt`: `pytest`, `pytest-cov`, `ruff`, `mypy`
- CI executes `ruff` + `pytest --cov ...`.

### 3.3 Governance Surface
- Protocol and baseline artifacts are synchronized and active.
- Strategic/engineering plan layer was previously absent (filled by WB-01).

## 4. Failure & Risk Analysis (Deep)

### 4.1 Confirmed Technical Failures
1. `ModuleNotFoundError: codex_agent` during test collection.
2. Submodule status markers start with `-` (not initialized), confirming dependency materialization failure.

### 4.2 Structural Weaknesses
1. Hardcoded `sys.path` extension in tests/scripts is brittle.
2. Manual script and integration test duplicate logic.
3. `README.md` lacks operational contract.
4. Quality gates are defined in CI but local deterministic bootstrap flow is undocumented.

### 4.3 Strategic Risks
1. Integration test reliability depends on external submodule availability.
2. No deterministic fallback mode when submodules are absent.
3. Minimal coverage metric can pass while real integration is broken.

## 5. Strategic Target State
- Repository becomes a deterministic integration validation node with:
  - reproducible dependency bootstrap,
  - clear local-vs-CI execution modes,
  - robust integration contract tests,
  - explicit expansion hooks for additional agents/channels.

## 6. Multi-Wave Plan

### Wave WB-01.A — Stabilization (Immediate)
Goal: remove hard blockers and make tests deterministic.
- A1. Add bootstrap script for submodule sync and verification.
- A2. Add preflight check in tests to produce explicit skip/fail reason when submodules unavailable.
- A3. Eliminate duplicate path bootstrap code by moving to shared helper.
DoD:
- Integration tests no longer fail with opaque `ModuleNotFoundError`.
- Preflight output clearly states missing dependency root-cause.

### Wave WB-01.B — Quality Engineering
Goal: convert placeholder quality into meaningful gates.
- B1. Replace `test_runtime_smoke_marker` with runtime contract smoke.
- B2. Add minimal import smoke for `codex_agent` and `interfaces`.
- B3. Split test markers: `unit`, `integration`, `submodule_required`.
DoD:
- `pytest -q -m "not integration"` is green in isolated environment.
- Integration suite has explicit marker and entrypoint.

### Wave WB-01.C — Evolution of Test Semantics
Goal: expand from ping-pong sanity to protocol conformance.
- C1. Add envelope contract assertions (status, payload schema, trace fields).
- C2. Add negative-path tests (unknown intent, invalid payload).
- C3. Add deterministic regression fixtures for protocol behavior.
DoD:
- Contract-focused integration tests cover success + failure paths.

### Wave WB-01.D — Growth & Expansion
Goal: scale repository from two-agent check to ecosystem validation.
- D1. Introduce matrix test design for additional agents (roaudter/operator/etc.).
- D2. Add scenario registry (`tests/scenarios/*.yaml`) for extensible flows.
- D3. Add lightweight compatibility matrix report artifact.
DoD:
- New agent route can be added without rewriting core test harness.

### Wave WB-01.E — Operationalization
Goal: ensure predictable execution in local + CI + autopilot contexts.
- E1. Add `scripts/test_entrypoint.sh` with mode flags:
  - `--unit-only`
  - `--integration`
  - `--ci`
- E2. Document AESS/autostart behavior and non-service nature.
- E3. Add quick triage guide for top 5 failure patterns.
DoD:
- One command can reproduce CI-like checks locally.

## 7. Forecast (Post-Implementation)
- After Wave A+B:
  - expected elimination of collection-time import failures,
  - shift from infrastructure failures to actionable behavioral failures.
- After Wave C+D:
  - repository becomes reusable integration quality gateway for LAM ecosystem.

## 8. Execution Priority Backlog (Ordered)
1. Submodule bootstrap + preflight checks.
2. Shared import/bootstrap helper (remove duplicate `sys.path` snippets).
3. Test marker strategy and split pipelines.
4. Contract-level ping-pong assertions.
5. Scenario registry for expansion.

## 9. KPI / Gate Metrics
- MTTR for integration test failures.
- Ratio: infra/config failures vs behavioral failures.
- Coverage of contract assertions (not just line coverage).
- Time to onboard a new agent into scenario matrix.

## 10. Immediate Next Action Block
1. Implement `scripts/bootstrap_submodules.sh`.
2. Add `tests/conftest.py` preflight for submodule presence.
3. Refactor ping-pong import bootstrap into single helper module.
