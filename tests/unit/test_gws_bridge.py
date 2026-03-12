from __future__ import annotations

import json
from pathlib import Path

from apps.lam_console.gws_bridge import GWSBridge


def test_gws_bridge_processes_health_request(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LAM_HUB_ROOT", str(tmp_path / ".gateway" / "hub"))
    monkeypatch.setenv("LAM_CAPTAIN_BRIDGE_ROOT", str(tmp_path / ".gateway" / "bridge" / "captain"))
    monkeypatch.setenv("LAM_GWS_LOCAL_DIR", str(tmp_path / ".gateway" / "exchange" / "gws"))
    monkeypatch.setenv("LAM_GWS_DRIVE_ROOT", str(tmp_path / "drive"))

    repo_root = Path(__file__).resolve().parents[2]
    bridge = GWSBridge(repo_root)

    req_file = tmp_path / ".gateway" / "bridge" / "captain" / "gws_requests.jsonl"
    req_file.parent.mkdir(parents=True, exist_ok=True)
    req_file.write_text(json.dumps({"id": "r1", "op": "health"}) + "\n", encoding="utf-8")

    payload = bridge.run_once()
    assert payload["processed"] == 1

    res_file = tmp_path / ".gateway" / "bridge" / "captain" / "gws_results.jsonl"
    rows = [json.loads(x) for x in res_file.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert rows[0]["id"] == "r1"
    assert rows[0]["response"]["ok"] is True


def test_gws_bridge_put_and_list(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LAM_HUB_ROOT", str(tmp_path / ".gateway" / "hub"))
    monkeypatch.setenv("LAM_CAPTAIN_BRIDGE_ROOT", str(tmp_path / ".gateway" / "bridge" / "captain"))
    monkeypatch.setenv("LAM_GWS_LOCAL_DIR", str(tmp_path / ".gateway" / "exchange" / "gws"))

    repo_root = Path(__file__).resolve().parents[2]
    bridge = GWSBridge(repo_root)

    src = tmp_path / "note.txt"
    src.write_text("ok", encoding="utf-8")

    put = bridge.handle({"op": "put", "src": str(src), "target_rel": "docs/note.txt"})
    assert put["ok"] is True

    listed = bridge.handle({"op": "list", "prefix": "docs", "limit": 10})
    assert listed["ok"] is True
    assert "docs/note.txt" in listed["files"]
