# LAM_Test_Agent

Integration test harness for LAM agent interaction flows.

## Bootstrap
```bash
scripts/bootstrap_submodules.sh
```

## Run tests
```bash
./.venv/bin/python -m pytest -q
```

### Split Modes
```bash
scripts/test_entrypoint.sh --unit-only
scripts/test_entrypoint.sh --integration
scripts/test_entrypoint.sh --ci
```

Notes:
- Integration tests that require submodule agent sources are marked `submodule_required`.
- If submodules are absent, those tests are skipped with explicit reason.

## Current Test Scale
- Collected tests: `160`
- Typical local result (unit-only local profile): `134 passed, 26 deselected`

## CI Gates
- `quality`: `ruff` + `mypy` + ecosystem deadloop guard (`--ecosystem`) + safety/resource stack validation + growth snapshot + bounded growth backlog generation + live activation policy report
- `quality`: `ruff` + `mypy` + ecosystem deadloop guard (`--ecosystem`) + safety/resource stack validation + growth snapshot + bounded growth backlog generation + live activation policy report + phase E drift report
- `unit-runtime-cov`: unit tests with runtime-only coverage gate (`>=65%`)
- `integration`: integration/route suites (submodule-dependent tests are skipped when sources are absent)

## Growth Data
- Route-level growth telemetry snapshot:
  - `memory/FRONT/TEST_MATRIX_GROWTH_SNAPSHOT.json`
- Bounded growth backlog artifact:
  - `memory/FRONT/TEST_MATRIX_GROWTH_BACKLOG.md`

## Ecosystem Governance
- Protocol expansion strategy:
  - `memory/FRONT/ECOSYSTEM_PROTOCOL_EXPANSION_STRATEGY_2026-02-17.md`
- Safety/resource stack (machine-readable):
  - `memory/FRONT/ECOSYSTEM_SAFETY_RESOURCE_STACK_V1.json`
- Ecosystem telemetry baseline:
  - `memory/FRONT/ECOSYSTEM_TELEMETRY_SNAPSHOT_2026-02-17.json`
  - `memory/FRONT/ECOSYSTEM_TELEMETRY_SNAPSHOT_2026-02-17.md`
- Live activation policy report:
  - `memory/FRONT/LIVE_ACTIVATION_POLICY_REPORT_2026-02-17.json`
  - `memory/FRONT/LIVE_ACTIVATION_POLICY_REPORT_2026-02-17.md`
- Phase E drift report:
  - `memory/FRONT/PHASE_E_DRIFT_REPORT_2026-02-17.json`
  - `memory/FRONT/PHASE_E_DRIFT_REPORT_2026-02-17.md`

## Strategy Artifacts
- WB-01 deep analysis and evolution plan:
  - `WB01_LAM_TEST_AGENT_DEEP_ANALYSIS_AND_STRATEGY_2026-02-17.md`
- Mirror gap strategy for discovering missing future-architecture tests:
  - `TEST_GAP_MIRROR_STRATEGY_2026-02-17.md`
- Route mirror matrix and compatibility report:
  - `TEST_MIRROR_MATRIX.md`
  - `COMPATIBILITY_MATRIX_REPORT_2026-02-17.md`
