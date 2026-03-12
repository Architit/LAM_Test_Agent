from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def load_mesh_module():
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "device_meshctl.py"
    spec = importlib.util.spec_from_file_location("device_meshctl", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pair_and_sync_once_dispatches_for_approved_device(tmp_path, monkeypatch) -> None:
    module = load_mesh_module()
    monkeypatch.setenv("LAM_CAPTAIN_BRIDGE_ROOT", str(tmp_path / ".gateway" / "bridge" / "captain"))
    ctl = module.DeviceMeshCtl(Path(__file__).resolve().parents[2])

    result = ctl.pair(
        device_id="pixel8",
        device_type="phone",
        platform="android",
        transport="wifi",
        scopes=["telemetry_read", "device_status"],
        endpoint="http://127.0.0.1:8765",
    )
    assert result["status"] in {"paired", "updated"}

    sync = ctl.sync_once("all", "bidirectional")
    assert sync["dispatched"] == 1

    outbox = tmp_path / ".gateway" / "bridge" / "captain" / "device_outbox" / "pixel8.jsonl"
    assert outbox.exists()
    last = json.loads(outbox.read_text(encoding="utf-8").splitlines()[-1])
    assert last["op"] == "mesh_sync"


def test_revoke_blocks_sync_dispatch(tmp_path, monkeypatch) -> None:
    module = load_mesh_module()
    monkeypatch.setenv("LAM_CAPTAIN_BRIDGE_ROOT", str(tmp_path / ".gateway" / "bridge" / "captain"))
    ctl = module.DeviceMeshCtl(Path(__file__).resolve().parents[2])
    ctl.pair(
        device_id="buds1",
        device_type="earbuds",
        platform="earbuds",
        transport="bluetooth",
        scopes=["audio_control", "device_status"],
        endpoint="",
    )
    ctl.revoke("buds1")
    sync = ctl.sync_once("all", "bidirectional")
    assert sync["dispatched"] == 0


def test_promote_full_access_enables_repo_root_path(tmp_path, monkeypatch) -> None:
    module = load_mesh_module()
    monkeypatch.setenv("LAM_CAPTAIN_BRIDGE_ROOT", str(tmp_path / ".gateway" / "bridge" / "captain"))
    repo_root = Path(__file__).resolve().parents[2]
    ctl = module.DeviceMeshCtl(repo_root)
    ctl.pair(
        device_id="trusted1",
        device_type="phone",
        platform="android",
        transport="wifi",
        scopes=["telemetry_read", "files_exchange"],
        endpoint="http://127.0.0.1:8765",
    )
    promoted = ctl.promote_full_access("trusted1")
    assert promoted["trust_level"] == "verified_full"
    ctl.sync_once("trusted1", "push")
    outbox = tmp_path / ".gateway" / "bridge" / "captain" / "device_outbox" / "trusted1.jsonl"
    manifest = json.loads(outbox.read_text(encoding="utf-8").splitlines()[-1])
    assert manifest["full_access"] is True
    assert manifest["paths"] == [str(repo_root)]


def test_pair_profile_applies_vendor_preset(tmp_path, monkeypatch) -> None:
    module = load_mesh_module()
    monkeypatch.setenv("LAM_CAPTAIN_BRIDGE_ROOT", str(tmp_path / ".gateway" / "bridge" / "captain"))
    ctl = module.DeviceMeshCtl(Path(__file__).resolve().parents[2])
    result = ctl.pair_profile("samsung_android", "s24", "http://127.0.0.1:8765")
    assert result["status"] in {"paired", "updated"}
    devices = ctl.list_devices()["devices"]
    target = next(d for d in devices if d["device_id"] == "s24")
    assert target["platform"] == "android"
    assert target["transport"] == "wifi"


def test_ambient_profile_grants_ambient_scope(tmp_path, monkeypatch) -> None:
    module = load_mesh_module()
    monkeypatch.setenv("LAM_CAPTAIN_BRIDGE_ROOT", str(tmp_path / ".gateway" / "bridge" / "captain"))
    ctl = module.DeviceMeshCtl(Path(__file__).resolve().parents[2])
    result = ctl.pair_profile("ambient_rgb", "aura_hub", "usb://ambient")
    assert result["status"] in {"paired", "updated"}
    devices = ctl.list_devices()["devices"]
    target = next(d for d in devices if d["device_id"] == "aura_hub")
    assert "ambient_light" in target["scopes"]
