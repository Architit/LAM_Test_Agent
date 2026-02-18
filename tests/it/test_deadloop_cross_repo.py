from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from lam_test_agent_paths import lam_root as default_lam_root
from lam_test_agent_paths import repo_root as default_repo_root

THIS_REPO_ROOT = default_repo_root()
LAM_ROOT = Path(os.getenv("LAM_ROOT", str(default_lam_root()))).resolve()
TEST_REPO_ROOT = Path(os.getenv("LAM_TEST_AGENT_ROOT", str(THIS_REPO_ROOT))).resolve()
GUARD_ENTRYPOINT = LAM_ROOT / "scripts" / "deadloop_guard_entrypoint.py"
ECOSYSTEM_SCAN = LAM_ROOT / "scripts" / "deadloop_ecosystem_scan.py"


def _require_lam_deadloop_tooling() -> None:
    if not LAM_ROOT.exists():
        pytest.skip("LAM repo not found for cross-repo deadloop assertions")
    if not GUARD_ENTRYPOINT.exists() or not ECOSYSTEM_SCAN.exists():
        pytest.skip("LAM deadloop scripts not available for cross-repo assertions")


def _run_lam(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=str(LAM_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.integration
def test_deadloop_guard_cross_repo_hold_for_governance_only_delta() -> None:
    _require_lam_deadloop_tooling()
    proc = _run_lam(
        [
            str(GUARD_ENTRYPOINT),
            "--governance-only-streak",
            "3",
            "--changed-path",
            "ROADMAP.md",
            "--changed-path",
            "DEV_LOGS.md",
            "--validation-result",
            "PASS",
        ]
    )
    payload = json.loads(proc.stdout)
    assert payload["preflight"]["decision"] == "HOLD_BY_DEADLOOP_BREAK_PROTOCOL"
    assert "structural delta" in payload["preflight"]["reason"]


@pytest.mark.integration
def test_deadloop_guard_cross_repo_passes_with_full_resume_tuple() -> None:
    _require_lam_deadloop_tooling()
    proc = _run_lam(
        [
            str(GUARD_ENTRYPOINT),
            "--governance-only-streak",
            "0",
            "--changed-path",
            "src/deadloop_gate.py",
            "--changed-path",
            "tests/test_deadloop_gate.py",
            "--validation-command",
            ".venv/bin/pytest -q tests/test_deadloop_gate.py -p no:cacheprovider",
            "--validation-result",
            "PASS",
            "--operator-confirmed",
        ]
    )
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["preflight"]["decision"] == "PASS"
    assert payload["resume"]["decision"] == "PASS"


@pytest.mark.integration
def test_deadloop_ecosystem_scan_includes_lam_and_lam_test_agent() -> None:
    _require_lam_deadloop_tooling()
    proc = _run_lam(
        [
            str(ECOSYSTEM_SCAN),
            "--repo",
            str(LAM_ROOT),
            "--repo",
            str(TEST_REPO_ROOT),
        ]
    )
    assert proc.returncode in {0, 7}
    payload = json.loads(proc.stdout)
    rows = payload["scan"]
    repos = {Path(row["repo"]).name for row in rows}
    assert "LAM" in repos
    assert "LAM_Test_Agent" in repos
