from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parents[2]

def test_phase_r_contract_markers() -> None:
    text = (REPO_ROOT / "contract" / "global" / "PHASE_R_RESEARCH_GATE_REGRESSION_CONTRACT_V1.md").read_text(encoding="utf-8")
    assert "PHASE_R_RESEARCH_GATE_REGRESSION_CONTRACT_V1" in text
    assert "phase_r_research_gate_regression_contract=ok" in text
    assert "phase_r_transport_benchmark_matrix=ok" in text
    assert "phase_r_vector_engine_benchmark_matrix=ok" in text
    assert "phase_r_wake_on_demand_trigger_check=ok" in text

def test_research_gate_mode_wiring_exists() -> None:
    text = (REPO_ROOT / "scripts" / "local" / "test_entrypoint.sh").read_text(encoding="utf-8")
    assert "--research-gate" in text
    assert "test_phase_r_research_gate_regression.py" in text
