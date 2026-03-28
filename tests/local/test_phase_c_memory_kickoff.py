from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parents[2]

def test_phase_c_contract_exists_and_has_required_markers() -> None:
    text = (REPO_ROOT / "contract" / "global" / "PHASE_C_MEMORY_KICKOFF_CONTRACT_V1.md").read_text(encoding="utf-8")
    assert "PHASE_C_MEMORY_KICKOFF_CONTRACT_V1" in text
    assert "phase_c_memory_kickoff_contract=ok" in text
    assert "phase_c_vector_engine_ready=ok" in text

def test_memory_mode_wiring_exists_in_test_entrypoint() -> None:
    text = (REPO_ROOT / "scripts" / "local" / "test_entrypoint.sh").read_text(encoding="utf-8")
    assert "--memory" in text
    assert "test_phase_c_memory_kickoff.py" in text
