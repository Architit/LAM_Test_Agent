from __future__ import annotations

import json
from pathlib import Path

from apps.lam_console.model_worker import ModelDeliveryWorker


def test_worker_keeps_spooled_records_when_endpoint_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("LAM_CODEX_ENDPOINT", raising=False)
    monkeypatch.setenv("LAM_HUB_ROOT", str(tmp_path / ".gateway" / "hub"))
    monkeypatch.setenv("LAM_CAPTAIN_BRIDGE_ROOT", str(tmp_path / ".gateway" / "bridge" / "captain"))

    repo_root = Path(__file__).resolve().parents[2]
    worker = ModelDeliveryWorker(repo_root)
    spool = worker.spool_dir / "codex.jsonl"
    rec = {"id": "x1", "provider": "codex", "message": "hello"}
    spool.write_text(json.dumps(rec) + "\n", encoding="utf-8")

    result = worker.run_once()
    assert result["status"] == "ok"
    assert result["skipped"] >= 1
    remaining = spool.read_text(encoding="utf-8").strip().splitlines()
    assert len(remaining) == 1

