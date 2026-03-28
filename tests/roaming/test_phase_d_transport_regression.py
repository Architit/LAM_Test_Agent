from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parents[2]

def test_phase_d_transport_contract_markers() -> None:
    text = (REPO_ROOT / "contract" / "global" / "PHASE_D_TRANSPORT_REGRESSION_CONTRACT_V1.md").read_text(encoding="utf-8")
    assert "PHASE_D_TRANSPORT_REGRESSION_CONTRACT_V1" in text
    assert "phase_d_transport_regression_contract=ok" in text
    assert "phase_d_shuttle_io_verified=ok" in text

def test_transport_mode_wiring_exists_in_test_entrypoint() -> None:
    text = (REPO_ROOT / "scripts" / "local" / "test_entrypoint.sh").read_text(encoding="utf-8")
    assert "--transport" in text
    assert "test_phase_d_transport_regression.py" in text
