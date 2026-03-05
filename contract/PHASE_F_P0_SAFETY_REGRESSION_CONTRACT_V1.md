# PHASE_F_P0_SAFETY_REGRESSION_CONTRACT_V1

## Scope
- owner_repo: `LAM_Test_Agent`
- phase: `PHASE_F_WAVE_1`
- task_id: `phaseF_lam_test_p0_safety_wave1_execution`
- status: `DONE`

## Objective
Extend regression gates for Phase F P0-safety markers (`circuit_breakers`, `hard_stop`, `manual_reauth`).

## Required Markers
- `phase_f_p0_safety_contract=ok`
- `phase_f_circuit_breaker_marker_scan=ok`
- `phase_f_hard_stop_marker_scan=ok`
- `phase_f_manual_reauth_marker_scan=ok`

## Test Wiring Contract
- `scripts/test_entrypoint.sh --p0-safety` MUST execute Phase F P0-safety checks.
- `scripts/test_entrypoint.sh --patch-runtime` MUST remain green as non-regression gate.
