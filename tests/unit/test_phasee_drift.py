from __future__ import annotations

from pathlib import Path

import pytest

from lam_test_agent_phasee_drift import build_drift_report, implemented_layers, unblock_conditions


@pytest.mark.unit
def test_unblock_conditions_mapped_from_blockers() -> None:
    policy = {
        "checks": [
            {"id": "network_resolution_gate", "ok": False},
            {"id": "submodule_readiness_gate", "ok": False},
            {"id": "dirty_repo_budget_gate", "ok": False},
            {"id": "p0_gap_budget_gate", "ok": False},
        ]
    }
    out = unblock_conditions(policy)
    assert len(out) >= 4


@pytest.mark.unit
def test_build_drift_report_shape() -> None:
    stack = {
        "layers": [
            {"id": "network_resolution_gate"},
            {"id": "submodule_readiness_gate"},
            {"id": "change_budget"},
        ]
    }
    policy = {"status": "BLOCKED", "recommended_mode": "mock_only", "checks": []}
    report = build_drift_report(__import__("pathlib").Path("."), stack, policy)
    assert report["stack_layers_total"] == 3
    assert "implementation_coverage_percent" in report
    assert report["live_policy_status"] == "BLOCKED"


@pytest.mark.unit
def test_implemented_layers_requires_runtime_and_text_for_contract_schema_lock(tmp_path: Path) -> None:
    (tmp_path / "tests" / "it").mkdir(parents=True)
    (tmp_path / "tests" / "it" / "test_route_matrix_contracts.py").write_text(
        "normalize_execution_payload\nmissing field: scenario_id\n",
        encoding="utf-8",
    )
    found_without_runtime = implemented_layers(tmp_path)
    assert "contract_schema_lock" not in found_without_runtime

    (tmp_path / "lam_test_agent_route_matrix.py").write_text(
        "def normalize_execution_payload(raw):\n    return raw\n",
        encoding="utf-8",
    )
    found_with_runtime = implemented_layers(tmp_path)
    assert "contract_schema_lock" in found_with_runtime
