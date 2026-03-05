from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parents[1]

def test_phase_f_contract_markers() -> None:
    text = (REPO_ROOT / "contract" / "PHASE_F_P0_SAFETY_REGRESSION_CONTRACT_V1.md").read_text(encoding="utf-8")
    assert "PHASE_F_P0_SAFETY_REGRESSION_CONTRACT_V1" in text
    assert "phase_f_p0_safety_contract=ok" in text
    assert "phase_f_circuit_breaker_marker_scan=ok" in text
    assert "phase_f_hard_stop_marker_scan=ok" in text
    assert "phase_f_manual_reauth_marker_scan=ok" in text

def test_p0_safety_mode_wiring_exists() -> None:
    text = (REPO_ROOT / "scripts" / "test_entrypoint.sh").read_text(encoding="utf-8")
    assert "--p0-safety" in text
    assert "test_phase_f_p0_safety_regression.py" in text
