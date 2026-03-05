from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_phase_c_contract_exists_and_has_required_markers() -> None:
    text = (REPO_ROOT / "contract" / "PHASE_C_MEMORY_KICKOFF_CONTRACT_V1.md").read_text(encoding="utf-8")
    assert "PHASE_C_MEMORY_KICKOFF_CONTRACT_V1" in text
    assert "phase_c_memory_contract=ok" in text
    assert "phase_c_marker_scan=ok" in text
    assert "phase_c_runtime_regressions=ok" in text
    assert "bridge_policy:c2_bridge_only=ack" in text


def test_memory_mode_wiring_exists_in_test_entrypoint() -> None:
    text = (REPO_ROOT / "scripts" / "test_entrypoint.sh").read_text(encoding="utf-8")
    assert "--memory" in text
    assert "test_phase_c_memory_kickoff.py" in text
