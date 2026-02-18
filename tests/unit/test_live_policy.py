from __future__ import annotations

import json
from pathlib import Path

import pytest

from lam_test_agent_live_policy import evaluate_live_activation_policy, main as live_policy_main


@pytest.mark.unit
def test_live_policy_ready_when_all_gates_pass() -> None:
    telemetry = {"summary": {"github_dns_resolvable": True, "dirty_repos": 0}}
    growth = {
        "summary": {
            "live_ready": True,
            "priority_counts": {"P0": 0},
            "deadloop_cross_repo": {
                "has_cross_repo_assertions": True,
                "guard_script_present": True,
                "ecosystem_scan_script_present": True,
                "cross_repo_ready": True,
            },
        },
        "missing_submodule_paths": [],
        "routes": [],
    }
    policy = evaluate_live_activation_policy(telemetry, growth, dirty_repo_budget=0, p0_budget=0)
    assert policy["status"] == "READY"
    assert policy["recommended_mode"] == "live_plus_mock"


@pytest.mark.unit
def test_live_policy_blocked_when_network_or_submodules_missing() -> None:
    telemetry = {"summary": {"github_dns_resolvable": False, "dirty_repos": 0}}
    growth = {
        "summary": {
            "live_ready": False,
            "priority_counts": {"P0": 5},
            "deadloop_cross_repo": {
                "has_cross_repo_assertions": False,
                "guard_script_present": False,
                "ecosystem_scan_script_present": False,
                "cross_repo_ready": False,
            },
        },
        "missing_submodule_paths": ["/x", "/y"],
        "routes": [],
    }
    policy = evaluate_live_activation_policy(telemetry, growth, dirty_repo_budget=0, p0_budget=0)
    assert policy["status"] == "BLOCKED"
    assert policy["recommended_mode"] == "mock_only"
    assert len(policy["blockers"]) >= 2


@pytest.mark.unit
def test_live_policy_blocks_when_degraded_conformance_missing() -> None:
    telemetry = {"summary": {"github_dns_resolvable": True, "dirty_repos": 0}}
    growth = {
        "summary": {
            "live_ready": True,
            "priority_counts": {"P0": 0},
            "deadloop_cross_repo": {
                "has_cross_repo_assertions": True,
                "guard_script_present": True,
                "ecosystem_scan_script_present": True,
                "cross_repo_ready": True,
            },
        },
        "missing_submodule_paths": [],
        "routes": [
            {
                "expected_status": "degraded",
                "has_failure_assertions": False,
                "has_contract_assertions": True,
            }
        ],
    }
    policy = evaluate_live_activation_policy(telemetry, growth, dirty_repo_budget=0, p0_budget=0)
    failed = [c for c in policy["checks"] if c["id"] == "degraded_mode_conformance_gate"][0]
    assert not failed["ok"]


@pytest.mark.unit
def test_live_policy_blocks_when_growth_checkpoint_gate_missing() -> None:
    telemetry = {"summary": {"github_dns_resolvable": True, "dirty_repos": 0}}
    growth = {
        "summary": {"live_ready": True, "priority_counts": {"P0": 0}},
        "missing_submodule_paths": [],
        "routes": [],
    }
    policy = evaluate_live_activation_policy(telemetry, growth, dirty_repo_budget=0, p0_budget=0)
    failed = [c for c in policy["checks"] if c["id"] == "growth_checkpoint_gate"][0]
    assert not failed["ok"]


@pytest.mark.unit
def test_live_policy_blocks_when_archivator_handoff_scope_active_and_not_ok() -> None:
    telemetry = {
        "summary": {
            "github_dns_resolvable": True,
            "dirty_repos": 0,
            "archivator_scope_active": True,
            "archivator_handoff_ok": False,
            "archivator_missing_mirrors_count": 1,
            "archivator_stale_mirrors_count": 2,
        }
    }
    growth = {
        "summary": {
            "live_ready": True,
            "priority_counts": {"P0": 0},
            "deadloop_cross_repo": {
                "has_cross_repo_assertions": True,
                "guard_script_present": True,
                "ecosystem_scan_script_present": True,
                "cross_repo_ready": True,
            },
        },
        "missing_submodule_paths": [],
        "routes": [],
    }
    policy = evaluate_live_activation_policy(telemetry, growth, dirty_repo_budget=0, p0_budget=0)
    failed = [c for c in policy["checks"] if c["id"] == "archivator_handoff_gate"][0]
    assert not failed["ok"]


@pytest.mark.unit
def test_live_policy_ready_with_local_mirror_when_dns_unavailable() -> None:
    telemetry = {
        "summary": {
            "github_dns_resolvable": False,
            "local_dependency_mirror_ready": True,
            "dirty_repos": 1,
        }
    }
    growth = {
        "summary": {
            "live_ready": True,
            "priority_counts": {"P0": 0},
            "deadloop_cross_repo": {
                "has_cross_repo_assertions": True,
                "guard_script_present": True,
                "ecosystem_scan_script_present": True,
                "cross_repo_ready": True,
            },
        },
        "missing_submodule_paths": [],
        "routes": [],
    }
    policy = evaluate_live_activation_policy(telemetry, growth, dirty_repo_budget=0, p0_budget=0)
    assert policy["status"] == "READY"
    failed = [c for c in policy["checks"] if c["id"] == "dirty_repo_budget_gate"][0]
    assert not failed["ok"]


@pytest.mark.unit
def test_live_policy_blocks_when_semantic_identity_is_not_governed() -> None:
    telemetry = {
        "summary": {
            "github_dns_resolvable": True,
            "dirty_repos": 0,
            "semantic_identity_scope_active": True,
            "semantic_identity_ok": False,
            "semantic_identity_unresolved_count": 0,
            "semantic_identity_provisional_count": 5,
            "semantic_identity_templated_true_name_count": 5,
        }
    }
    growth = {
        "summary": {
            "live_ready": True,
            "priority_counts": {"P0": 0},
            "deadloop_cross_repo": {
                "has_cross_repo_assertions": True,
                "guard_script_present": True,
                "ecosystem_scan_script_present": True,
                "cross_repo_ready": True,
            },
        },
        "missing_submodule_paths": [],
        "routes": [],
    }
    policy = evaluate_live_activation_policy(telemetry, growth, dirty_repo_budget=0, p0_budget=0)
    failed = [c for c in policy["checks"] if c["id"] == "semantic_identity_governance_gate"][0]
    assert not failed["ok"]
    assert policy["status"] == "BLOCKED"


@pytest.mark.unit
def test_live_policy_main_returns_code_2_for_invalid_input_json(tmp_path: Path) -> None:
    telemetry = tmp_path / "telemetry.json"
    growth = tmp_path / "growth.json"
    telemetry.write_text("not-json", encoding="utf-8")
    growth.write_text(json.dumps({"summary": {}}), encoding="utf-8")

    rc = live_policy_main(
        [
            "--telemetry",
            str(telemetry),
            "--growth",
            str(growth),
            "--output-json",
            str(tmp_path / "policy.json"),
            "--output-md",
            str(tmp_path / "policy.md"),
        ]
    )
    assert rc == 2


@pytest.mark.unit
def test_live_policy_main_requires_object_json(tmp_path: Path) -> None:
    telemetry = tmp_path / "telemetry.json"
    growth = tmp_path / "growth.json"
    telemetry.write_text(json.dumps([]), encoding="utf-8")
    growth.write_text(json.dumps({"summary": {}}), encoding="utf-8")

    rc = live_policy_main(
        [
            "--telemetry",
            str(telemetry),
            "--growth",
            str(growth),
            "--output-json",
            str(tmp_path / "policy.json"),
            "--output-md",
            str(tmp_path / "policy.md"),
        ]
    )
    assert rc == 2
