from __future__ import annotations

import os
from pathlib import Path
import stat
import subprocess
import sys
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


@pytest.mark.unit
@pytest.mark.parametrize(
    "script_rel",
    [
        "scripts/bootstrap_submodules.sh",
        "scripts/test_entrypoint.sh",
        "scripts/gateway_io.sh",
        "scripts/aess_autostart.sh",
    ],
)
def test_runtime_scripts_are_executable(script_rel: str) -> None:
    script = ROOT / script_rel
    assert script.exists(), f"missing runtime script: {script}"
    mode = script.stat().st_mode
    assert mode & stat.S_IXUSR, f"script is not executable by owner: {script}"


@pytest.mark.unit
@pytest.mark.parametrize(
    "module_name",
    [
        "lam_test_agent_growth_data",
        "lam_test_agent_growth_checkpoint_gate",
        "lam_test_agent_live_policy",
        "lam_test_agent_phasee_drift",
        "lam_test_agent_ecosystem_telemetry",
        "lam_test_agent_telemetry_freshness_gate",
        "lam_test_agent_telemetry_integrity_gate",
        "lam_test_agent_openai_feedback_bundle",
        "lam_test_agent_openai_feedback_sender",
        "lam_test_agent_feedback_delivery_gate",
        "lam_test_agent_lam_forensics",
    ],
)
def test_key_cli_modules_expose_help(module_name: str) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    proc = subprocess.run(
        [sys.executable, "-m", module_name, "--help"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"{module_name} --help failed: {proc.stderr or proc.stdout}"


@pytest.mark.unit
def test_runtime_log_is_redirected_outside_repo_by_default() -> None:
    runtime_log = os.environ.get("LAM_RUNTIME_LOG_FILE", "")
    assert runtime_log.startswith("/tmp/")
