from __future__ import annotations

import os
import stat
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

from lam_test_agent_paths import repo_root


ROOT = repo_root()
GATEWAY_SCRIPT = ROOT / "scripts" / "gateway_io.sh"
AUTOSTART_SCRIPT = ROOT / "scripts" / "aess_autostart.sh"
ENTRYPOINT_SCRIPT = ROOT / "scripts" / "test_entrypoint.sh"


def _make_executable(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR)


@pytest.mark.unit
def test_gateway_verify_requires_onedrive_and_gworkspace() -> None:
    env = os.environ.copy()
    env.pop("GATEWAY_ONEDRIVE_ROOT", None)
    env.pop("GATEWAY_GWORKSPACE_ROOT", None)
    proc = subprocess.run(
        ["bash", str(GATEWAY_SCRIPT), "verify"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    out = proc.stdout + proc.stderr
    assert proc.returncode == 1
    assert "onedrive:warn env_not_set GATEWAY_ONEDRIVE_ROOT" in out
    assert "gworkspace:warn env_not_set GATEWAY_GWORKSPACE_ROOT" in out


@pytest.mark.unit
def test_aess_autostart_does_not_stamp_when_service_start_fails(tmp_path: Path) -> None:
    repo_dir = tmp_path / "repo-under-test"
    scripts_dir = repo_dir / "scripts"
    state_root = tmp_path / "state"
    scripts_dir.mkdir(parents=True)

    autostart = scripts_dir / "aess_autostart.sh"
    autostart.write_text(AUTOSTART_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
    _make_executable(autostart)

    failing_service = scripts_dir / "aess_service_start.sh"
    failing_service.write_text("#!/usr/bin/env bash\nexit 1\n", encoding="utf-8")
    _make_executable(failing_service)

    env = os.environ.copy()
    env["AESS_STATE_ROOT"] = str(state_root)
    proc = subprocess.run(
        ["bash", str(autostart)],
        cwd=repo_dir,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode != 0
    assert not (state_root / f"{repo_dir.name}.last").exists()


@pytest.mark.unit
def test_test_entrypoint_falls_back_to_workspace_venv(tmp_path: Path) -> None:
    workspace = tmp_path / "ecosystem"
    agent_root = workspace / "agents" / "test-agent"
    scripts_dir = agent_root / "scripts"
    tests_dir = agent_root / "tests"
    fallback_venv_bin = workspace / ".venv" / "bin"
    scripts_dir.mkdir(parents=True)
    tests_dir.mkdir(parents=True)
    fallback_venv_bin.mkdir(parents=True)

    copied_entrypoint = scripts_dir / "test_entrypoint.sh"
    copied_entrypoint.write_text(ENTRYPOINT_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
    _make_executable(copied_entrypoint)

    (tests_dir / "test_smoke.py").write_text(
        "def test_smoke_from_workspace_venv_fallback():\n    assert True\n",
        encoding="utf-8",
    )

    fallback_python = fallback_venv_bin / "python"
    fallback_python.write_text(
        "#!/usr/bin/env bash\n"
        f"exec {sys.executable} \"$@\"\n",
        encoding="utf-8",
    )
    _make_executable(fallback_python)

    proc = subprocess.run(
        ["bash", str(copied_entrypoint), "--ci"],
        cwd=agent_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0


@pytest.mark.unit
def test_gateway_import_rejects_traversal_entries(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe.tgz"
    payload = tmp_path / "payload.txt"
    payload.write_text("x", encoding="utf-8")
    with tarfile.open(archive, "w:gz") as tf:
        tf.add(payload, arcname="../escape.txt")

    proc = subprocess.run(
        ["bash", str(GATEWAY_SCRIPT), "import", str(archive)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    out = proc.stdout + proc.stderr
    assert proc.returncode != 0
    assert "unsafe_path traversal" in out


@pytest.mark.unit
def test_test_entrypoint_declares_all_mode() -> None:
    text = ENTRYPOINT_SCRIPT.read_text(encoding="utf-8")
    assert "--all" in text


@pytest.mark.unit
def test_test_entrypoint_uses_allow_empty_and_cacheprovider_guard() -> None:
    text = ENTRYPOINT_SCRIPT.read_text(encoding="utf-8")
    assert "run_pytest_allow_empty" in text
    assert "PYTEST_ADDOPTS" in text
    assert "no:cacheprovider" in text


@pytest.mark.unit
def test_test_entrypoint_unknown_mode_exits_2() -> None:
    proc = subprocess.run(
        ["bash", str(ENTRYPOINT_SCRIPT), "--unknown-mode"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    out = proc.stdout + proc.stderr
    assert proc.returncode == 2
    assert "usage:" in out.lower()
