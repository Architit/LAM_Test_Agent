import os
import subprocess
import tarfile
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "roaming" / "gateway_io.sh"


def _build_archive(dst: Path, member_name: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "file.txt"
        f.write_text("content", encoding="utf-8")
        with tarfile.open(dst, "w:gz") as tar:
            tar.add(f, arcname=member_name)


def test_gateway_io_import_without_argument_fails():
    proc = subprocess.run(
        ["bash", str(SCRIPT), "import"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert proc.returncode == 1


def test_gateway_io_import_rejects_unsafe_archive_path(tmp_path: Path):
    archive = tmp_path / "bad.tgz"
    _build_archive(archive, "../escape.txt")

    env = os.environ.copy()
    env["GATEWAY_IMPORT_DIR"] = str(tmp_path / "import")
    env["GATEWAY_STAGE_DIR"] = str(tmp_path / "stage")
    env["GATEWAY_EXPORT_DIR"] = str(tmp_path / "export")

    proc = subprocess.run(
        ["bash", str(SCRIPT), "import", str(archive)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=env,
    )
    assert proc.returncode == 1
