# PHASE_R_RESEARCH_GATE_REGRESSION_CONTRACT_V1

status: ACTIVE
derivation_mode: DERIVATION_ONLY

## Scope
- repository: `LAM_Test_Agent`
- phase: `R` (Research Gate)
- task_id: `phaseR_lam_test_wave1_execution`

## Required Markers
- `phase_r_research_gate_regression_contract=ok`
- `phase_r_transport_benchmark_matrix=ok`
- `phase_r_vector_engine_benchmark_matrix=ok`
- `phase_r_wake_on_demand_trigger_check=ok`

## Benchmark Matrix
- transport: `ZeroMQ` vs `gRPC` vs `FastAPI`
- vector engine: `FAISS` vs `LanceDB` vs `SQLite-vec/SQLite-VSS`
- wake-on-demand: trigger readiness + cold-start latency tuple

## Fail-Fast
- missing benchmark dimension => `BLOCKED`
- missing comparable metrics => `BLOCKED`
- missing owner evidence tuple => `BLOCKED`
