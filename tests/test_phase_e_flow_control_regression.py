from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_phase_e_contract_markers() -> None:
    text = (REPO_ROOT / "contract" / "PHASE_E_FLOW_CONTROL_REGRESSION_CONTRACT_V1.md").read_text(encoding="utf-8")
    assert "PHASE_E_FLOW_CONTROL_REGRESSION_CONTRACT_V1" in text
    assert "phase_e_flow_control_contract=ok" in text
    assert "phase_e_cbfc_marker_scan=ok" in text
    assert "phase_e_heartbeat_marker_scan=ok" in text
    assert "phase_e_outlier_isolation_marker_scan=ok" in text


def test_flow_control_mode_wiring_exists() -> None:
    text = (REPO_ROOT / "scripts" / "test_entrypoint.sh").read_text(encoding="utf-8")
    assert "--flow-control" in text
    assert "test_phase_e_flow_control_regression.py" in text
