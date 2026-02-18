from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from lam_test_agent_feedback_delivery_gate import main as gate_main


def _event_id(bundle: dict) -> str:
    blob = json.dumps(bundle, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@pytest.mark.unit
def test_gate_fails_when_pending_critical_spool_exists(tmp_path: Path) -> None:
    bundle = {"summary": {"critical_incidents": 0}, "incidents": []}
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    spool = tmp_path / "spool"
    spool.mkdir(parents=True, exist_ok=True)
    (spool / "feedback_x.json").write_text(json.dumps({"critical_count": 2}), encoding="utf-8")

    rc = gate_main(
        [
            "--bundle-json",
            str(bundle_path),
            "--spool-dir",
            str(spool),
            "--receipts-dir",
            str(tmp_path / "receipts"),
        ]
    )
    assert rc == 1


@pytest.mark.unit
def test_gate_passes_for_critical_when_receipt_exists(tmp_path: Path) -> None:
    bundle = {"summary": {"critical_incidents": 1}, "incidents": [{"incident_id": "a"}]}
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
    event_id = _event_id(bundle)

    receipts = tmp_path / "receipts"
    receipts.mkdir(parents=True, exist_ok=True)
    (receipts / "openai_feedback_receipt_test.json").write_text(
        json.dumps({"event_id": event_id, "ok": True}),
        encoding="utf-8",
    )

    rc = gate_main(
        [
            "--bundle-json",
            str(bundle_path),
            "--spool-dir",
            str(tmp_path / "spool"),
            "--receipts-dir",
            str(receipts),
        ]
    )
    assert rc == 0
