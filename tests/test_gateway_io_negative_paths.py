from __future__ import annotations

import io
import os
import subprocess
import tarfile
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "gateway_io.sh"


def _build_archive(archive: Path, member_name: str) -> None:
    data = b"x"
    info = tarfile.TarInfo(member_name)
    info.size = len(data)
    info.mtime = int(time.time())
    with tarfile.open(archive, "w:gz") as tf:
        tf.addfile(info, io.BytesIO(data))


def test_gateway_io_import_without_argument_fails():
    proc = subprocess.run(
        ["bash", str(SCRIPT), "import"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert proc.returncode == 1
    assert "missing_archive_argument" in (proc.stdout + proc.stderr)


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
    assert "unsafe_path" in (proc.stdout + proc.stderr)
