# PHASE_E_FLOW_CONTROL_REGRESSION_CONTRACT_V1

## Scope
- owner_repo: `LAM_Test_Agent`
- phase: `PHASE_E_WAVE_1`
- task_id: `phaseE_lam_test_flow_control_wave1_execution`
- status: `DONE`

## Objective
Extend regression gates for Phase E flow-control markers (`CBFC`, heartbeat, outlier isolation).

## Required Markers
- `phase_e_flow_control_contract=ok`
- `phase_e_cbfc_marker_scan=ok`
- `phase_e_heartbeat_marker_scan=ok`
- `phase_e_outlier_isolation_marker_scan=ok`

## Test Wiring Contract
- `scripts/test_entrypoint.sh --flow-control` MUST execute Phase E flow-control checks.
- `scripts/test_entrypoint.sh --patch-runtime` MUST remain green as non-regression gate.

## Constraints
- derivation_only execution
- fail-fast on violated preconditions
- no-new-agents-or-repos
