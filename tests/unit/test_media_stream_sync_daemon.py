from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def load_module():
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "apps" / "lam_console" / "media_stream_sync_daemon.py"
    spec = importlib.util.spec_from_file_location("media_stream_sync_daemon", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_choose_copy_direction_bidirectional() -> None:
    m = load_module()
    src = {"size": 10, "mtime_ns": 200}
    dst = {"size": 10, "mtime_ns": 100}
    assert m.choose_copy_direction(src, dst, "bidirectional") == "src_to_dst"


def test_media_sync_run_once_copies_file(tmp_path: Path, monkeypatch) -> None:
    m = load_module()
    repo_root = Path(__file__).resolve().parents[2]
    hub = tmp_path / ".gateway" / "hub"
    bridge = tmp_path / ".gateway" / "bridge" / "captain"
    device = tmp_path / ".gateway" / "exchange" / "device"
    removable = tmp_path / ".gateway" / "exchange" / "removable"
    device.mkdir(parents=True, exist_ok=True)
    removable.mkdir(parents=True, exist_ok=True)
    (device / "data.txt").write_text("hello", encoding="utf-8")

    monkeypatch.setenv("LAM_HUB_ROOT", str(hub))
    monkeypatch.setenv("LAM_CAPTAIN_BRIDGE_ROOT", str(bridge))
    monkeypatch.setenv("LAM_MEDIA_DEVICE_ROOT", str(device))
    monkeypatch.setenv("LAM_MEDIA_REMOVABLE_ROOT", str(removable))
    monkeypatch.setenv("LAM_MEDIA_SYNC_MODE", "push")
    monkeypatch.setenv("LAM_MEDIA_SYNC_MAX_OPS_PER_TICK", "8")

    svc = m.MediaStreamSync(repo_root)
    payload = svc.run_once()
    assert payload["applied_ops"] >= 1
    assert (removable / "data.txt").exists()
    state = json.loads((hub / "media_stream_sync_state.json").read_text(encoding="utf-8"))
    assert state["mode"] == "push"


def test_class_order_prioritizes_instructions_contracts_policies(tmp_path: Path, monkeypatch) -> None:
    m = load_module()
    repo_root = Path(__file__).resolve().parents[2]
    hub = tmp_path / ".gateway" / "hub"
    bridge = tmp_path / ".gateway" / "bridge" / "captain"
    device = tmp_path / ".gateway" / "exchange" / "device"
    removable = tmp_path / ".gateway" / "exchange" / "removable"
    device.mkdir(parents=True, exist_ok=True)
    removable.mkdir(parents=True, exist_ok=True)

    (device / "instructions" / "a.txt").parent.mkdir(parents=True, exist_ok=True)
    (device / "instructions" / "a.txt").write_text("a", encoding="utf-8")
    (device / "contracts" / "b.txt").parent.mkdir(parents=True, exist_ok=True)
    (device / "contracts" / "b.txt").write_text("b", encoding="utf-8")
    (device / "policies" / "c.txt").parent.mkdir(parents=True, exist_ok=True)
    (device / "policies" / "c.txt").write_text("c", encoding="utf-8")

    monkeypatch.setenv("LAM_HUB_ROOT", str(hub))
    monkeypatch.setenv("LAM_CAPTAIN_BRIDGE_ROOT", str(bridge))
    monkeypatch.setenv("LAM_MEDIA_DEVICE_ROOT", str(device))
    monkeypatch.setenv("LAM_MEDIA_REMOVABLE_ROOT", str(removable))
    monkeypatch.setenv("LAM_MEDIA_SYNC_MODE", "push")
    monkeypatch.setenv("LAM_MEDIA_SYNC_MAX_OPS_PER_TICK", "2")
    monkeypatch.setenv("LAM_MEDIA_SYNC_CLASS_ORDER", "instructions,contracts,policies,other")
    monkeypatch.setenv("LAM_MEDIA_SYNC_CLASS_MAX_OPS", "instructions:1,contracts:1,policies:1,other:0")

    svc = m.MediaStreamSync(repo_root)
    payload = svc.run_once()
    assert payload["applied_ops"] == 2
    assert payload["applied_by_class"]["instructions"] == 1
    assert payload["applied_by_class"]["contracts"] == 1
    assert payload["applied_by_class"]["policies"] == 0
    assert (removable / "instructions" / "a.txt").exists()
    assert (removable / "contracts" / "b.txt").exists()
    assert not (removable / "policies" / "c.txt").exists()


def test_parse_class_order_appends_new_priority_domains() -> None:
    m = load_module()
    order = m.parse_class_order("instructions,contracts,protocols,policies")
    assert "licenses" in order
    assert "map" in order
    assert "cards" in order
    assert "keypass_code_dnagen" in order
