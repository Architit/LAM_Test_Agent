from __future__ import annotations

import json
from pathlib import Path

import pytest

from lam_test_agent_openai_feedback_sender import main as sender_main


@pytest.mark.unit
def test_sender_spools_and_fails_on_missing_url_for_critical(tmp_path: Path) -> None:
    bundle = {
        "summary": {"critical_incidents": 1},
        "incidents": [{"incident_id": "a1", "severity": "critical", "count": 1}],
    }
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    rc = sender_main(
        [
            "--bundle-json",
            str(bundle_path),
            "--spool-dir",
            str(tmp_path / "spool"),
            "--receipts-dir",
            str(tmp_path / "receipts"),
            "--upload-url",
            "",
        ]
    )
    assert rc == 1
    spool_files = list((tmp_path / "spool").glob("feedback_*.json"))
    assert len(spool_files) == 1


@pytest.mark.unit
def test_sender_passes_without_url_for_noncritical(tmp_path: Path) -> None:
    bundle = {
        "summary": {"critical_incidents": 0},
        "incidents": [{"incident_id": "a1", "severity": "info", "count": 1}],
    }
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    rc = sender_main(
        [
            "--bundle-json",
            str(bundle_path),
            "--spool-dir",
            str(tmp_path / "spool"),
            "--receipts-dir",
            str(tmp_path / "receipts"),
            "--upload-url",
            "",
        ]
    )
    assert rc == 0
