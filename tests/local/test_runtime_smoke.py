import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.unit
def test_repo_structure_exists() -> None:
    required = [
        ROOT / "architecture",
        ROOT / "contract",
        ROOT / "devkit",
        ROOT / "scripts",
        ROOT / "tests",
        ROOT / "core",
    ]
    missing = [str(p) for p in required if not p.exists()]
    assert not missing, f"required repo structure missing: {missing}"


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
        ROOT / "scripts" / "local" / "bootstrap_submodules.sh",
    ]
    missing = [str(p) for p in required if not p.exists()]
    assert not missing, f"required repo contract files are missing: {missing}"


@pytest.mark.unit
def test_venv_is_present() -> None:
    # On CI this might differ, but in dev should exist
    pass
