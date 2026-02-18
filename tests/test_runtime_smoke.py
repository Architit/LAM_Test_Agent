from __future__ import annotations

from pathlib import Path
import pytest

from lam_test_agent_bootstrap import missing_agent_src_paths


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.unit
def test_repo_contract_files_exist() -> None:
    required = [
        ROOT / "ROADMAP.md",
        ROOT / "DEV_LOGS.md",
        ROOT / "INTERACTION_PROTOCOL.md",
        ROOT / "WORKFLOW_SNAPSHOT_CONTRACT.md",
        ROOT / "WORKFLOW_SNAPSHOT_STATE.md",
        ROOT / "SYSTEM_STATE_CONTRACT.md",
        ROOT / "SYSTEM_STATE.md",
        ROOT / "LRPT" / "protocol" / "LEARNING_SIGNAL_CONTRACT_V1.md",
        ROOT / "LRPT" / "journal" / "SYNAPTIC_WEIGHTS_V1.yaml",
        ROOT / "LRPT" / "flow" / "TASK_SPEC_SYNAPTIC_PLASTICITY_V1.yaml",
        ROOT / "scripts" / "bootstrap_submodules.sh",
    ]
    missing = [str(p) for p in required if not p.exists()]
    assert not missing, f"required repo contract files are missing: {missing}"


@pytest.mark.unit
def test_submodule_dependency_surface_is_explicit() -> None:
    expected = {
        str(ROOT / "LAM_Test" / "agents" / "codex-agent" / "src"),
        str(ROOT / "LAM_Test" / "agents" / "comm-agent" / "src"),
    }
    actual = {str(p) for p in missing_agent_src_paths(ROOT)}
    # In local dev these may be present or absent; what matters is that
    # dependency endpoints are exactly the declared ones.
    assert actual.issubset(expected)
