from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_module():
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "apps" / "lam_console" / "governance_autopilot_daemon.py"
    spec = importlib.util.spec_from_file_location("governance_autopilot_daemon", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_evaluate_domain_missing_is_degraded() -> None:
    m = load_module()
    now = 1000.0
    status = m.evaluate_domain([Path("/tmp/not_exists_a"), Path("/tmp/not_exists_b")], now=now, stale_sec=10)
    assert status["health"] == "degraded_missing"
    assert status["exists_count"] == 0


def test_corrective_vector_for_missing_is_p1() -> None:
    m = load_module()
    vector = m.corrective_vector("planning", {"health": "degraded_missing", "required_count": 2, "exists_count": 0, "stale_count": 0})
    assert vector["priority"] == "P1"
    assert vector["action"] == "materialize_missing_artifacts"


def test_domain_matrix_includes_structural_system_artifacts() -> None:
    m = load_module()
    repo_root = Path(__file__).resolve().parents[2]
    matrix = m.build_domain_matrix(repo_root)
    contracting = [str(p) for p in matrix.get("contracting", [])]
    mapping = [str(p) for p in matrix.get("mapping", [])]
    assert str(repo_root / "infra/governance/STRUCTURAL_SYSTEMS_CONTRACTS_V1.md") in contracting
    assert str(repo_root / "infra/governance/STRUCTURAL_SYSTEMS_MAP_V1.md") in mapping
