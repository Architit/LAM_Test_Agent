from __future__ import annotations

import json
from pathlib import Path

import pytest

from lam_test_agent_telemetry_integrity_gate import build_manifest, verify_manifest


@pytest.mark.unit
def test_build_manifest_and_verify_ok(tmp_path: Path) -> None:
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("alpha\n", encoding="utf-8")
    b.write_text("beta\n", encoding="utf-8")
    manifest = build_manifest([a, b])
    assert verify_manifest(manifest) == []


@pytest.mark.unit
def test_verify_manifest_detects_hash_mismatch(tmp_path: Path) -> None:
    a = tmp_path / "a.txt"
    a.write_text("alpha\n", encoding="utf-8")
    manifest = build_manifest([a])
    a.write_text("tampered\n", encoding="utf-8")
    errors = verify_manifest(manifest)
    assert any("hash mismatch" in e for e in errors)


@pytest.mark.unit
def test_verify_manifest_detects_missing_file(tmp_path: Path) -> None:
    a = tmp_path / "a.txt"
    a.write_text("alpha\n", encoding="utf-8")
    manifest = build_manifest([a])
    a.unlink()
    errors = verify_manifest(manifest)
    assert any("missing file" in e for e in errors)


@pytest.mark.unit
def test_manifest_is_json_serializable(tmp_path: Path) -> None:
    a = tmp_path / "a.txt"
    a.write_text("alpha\n", encoding="utf-8")
    manifest = {"files": build_manifest([a])}
    encoded = json.dumps(manifest)
    assert "files" in encoded
