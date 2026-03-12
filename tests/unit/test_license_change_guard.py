from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_module():
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "license_change_guard.py"
    spec = importlib.util.spec_from_file_location("license_change_guard", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_approval_allowed_true_for_matching_row() -> None:
    m = load_module()
    approvals = [
        {
            "repo_name": "LAM_Test_Agent",
            "license_sha256": "abc123",
            "approved": True,
            "approval_id": "APR-001",
        }
    ]
    assert m.approval_allowed(approvals, "LAM_Test_Agent", "abc123") is True


def test_approval_allowed_false_for_unmatched_sha() -> None:
    m = load_module()
    approvals = [{"repo_name": "LAM_Test_Agent", "license_sha256": "abc123", "approved": True}]
    assert m.approval_allowed(approvals, "LAM_Test_Agent", "zzz999") is False


def test_index_by_repo_ignores_invalid_rows() -> None:
    m = load_module()
    rows = [{"repo_name": "A", "x": 1}, {"x": 2}, "bad"]
    out = m.index_by_repo(rows)
    assert set(out.keys()) == {"A"}
