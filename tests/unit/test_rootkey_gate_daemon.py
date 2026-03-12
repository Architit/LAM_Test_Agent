from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def load_module():
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "apps" / "lam_console" / "rootkey_gate_daemon.py"
    spec = importlib.util.spec_from_file_location("rootkey_gate_daemon", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_rootkey_activates_when_pairing_and_key_match(tmp_path, monkeypatch) -> None:
    m = load_module()
    repo_root = Path(__file__).resolve().parents[2]
    hub = tmp_path / ".gateway" / "hub"
    bridge = tmp_path / ".gateway" / "bridge" / "captain"
    media = tmp_path / "removable"
    key_file = media / ".radriloniuma" / "rootkey" / "architit_root.key"
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key_payload = "architit-root-seed"
    key_file.write_text(key_payload, encoding="utf-8")
    digest = m.sha256_text(key_payload)

    hub.mkdir(parents=True, exist_ok=True)
    (hub / "rootkey_pairing.json").write_text(
        json.dumps({"enabled": True, "owner": "architit", "key_id": "AK-001"}, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("LAM_HUB_ROOT", str(hub))
    monkeypatch.setenv("LAM_CAPTAIN_BRIDGE_ROOT", str(bridge))
    monkeypatch.setenv("LAM_ROOTKEY_ENABLE", "1")
    monkeypatch.setenv("LAM_ROOTKEY_MEDIA_ROOT", str(media))
    monkeypatch.setenv("LAM_ROOTKEY_ARCHITIT_SHA256", digest)
    monkeypatch.setenv("LAM_ROOTKEY_REQUIRE_CHALLENGE", "0")

    svc = m.RootKeyGate(repo_root)
    payload = svc.run_once()
    assert payload["active"] is True
    assert payload["mode"] == "SEED_GOD_MODE_SPREAD_FLOW_INIT"
    assert (hub / "rootkey_active.flag").exists()


def test_rootkey_requires_challenge_response_when_enabled(tmp_path, monkeypatch) -> None:
    m = load_module()
    repo_root = Path(__file__).resolve().parents[2]
    hub = tmp_path / ".gateway" / "hub"
    bridge = tmp_path / ".gateway" / "bridge" / "captain"
    media = tmp_path / "removable"
    key_file = media / ".radriloniuma" / "rootkey" / "architit_root.key"
    response_file = media / ".radriloniuma" / "rootkey" / "challenge_response.sha256"
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key_payload = "architit-root-seed"
    key_file.write_text(key_payload, encoding="utf-8")
    digest = m.sha256_text(key_payload)

    hub.mkdir(parents=True, exist_ok=True)
    (hub / "rootkey_pairing.json").write_text(
        json.dumps({"enabled": True, "owner": "architit", "key_id": "AK-002"}, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    nonce = "abc123nonce"
    (hub / "rootkey_challenge.json").write_text(
        json.dumps({"nonce": nonce, "issued_utc": m.utc_now(), "ttl_sec": 180, "used": False}, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("LAM_HUB_ROOT", str(hub))
    monkeypatch.setenv("LAM_CAPTAIN_BRIDGE_ROOT", str(bridge))
    monkeypatch.setenv("LAM_ROOTKEY_ENABLE", "1")
    monkeypatch.setenv("LAM_ROOTKEY_MEDIA_ROOT", str(media))
    monkeypatch.setenv("LAM_ROOTKEY_ARCHITIT_SHA256", digest)
    monkeypatch.setenv("LAM_ROOTKEY_REQUIRE_CHALLENGE", "1")

    svc = m.RootKeyGate(repo_root)
    fail_payload = svc.run_once()
    assert fail_payload["active"] is False
    assert fail_payload["reason"] == "challenge_response_missing"

    response = m.sha256_text(f"{nonce}:{digest}")
    response_file.write_text(response + "\n", encoding="utf-8")
    ok_payload = svc.run_once()
    assert ok_payload["active"] is True
    assert ok_payload["reason"] == "ok"


def test_rootkey_auto_rotates_missing_challenge(tmp_path, monkeypatch) -> None:
    m = load_module()
    repo_root = Path(__file__).resolve().parents[2]
    hub = tmp_path / ".gateway" / "hub"
    bridge = tmp_path / ".gateway" / "bridge" / "captain"
    media = tmp_path / "removable"
    key_file = media / ".radriloniuma" / "rootkey" / "architit_root.key"
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key_payload = "architit-root-seed"
    key_file.write_text(key_payload, encoding="utf-8")
    digest = m.sha256_text(key_payload)

    hub.mkdir(parents=True, exist_ok=True)
    (hub / "rootkey_pairing.json").write_text(
        json.dumps({"enabled": True, "owner": "architit", "key_id": "AK-003"}, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("LAM_HUB_ROOT", str(hub))
    monkeypatch.setenv("LAM_CAPTAIN_BRIDGE_ROOT", str(bridge))
    monkeypatch.setenv("LAM_ROOTKEY_ENABLE", "1")
    monkeypatch.setenv("LAM_ROOTKEY_MEDIA_ROOT", str(media))
    monkeypatch.setenv("LAM_ROOTKEY_ARCHITIT_SHA256", digest)
    monkeypatch.setenv("LAM_ROOTKEY_REQUIRE_CHALLENGE", "1")

    svc = m.RootKeyGate(repo_root)
    payload = svc.run_once()
    assert payload["active"] is False
    assert (hub / "rootkey_challenge.json").exists()


def test_rootkey_fail_ban_after_mismatch_threshold(tmp_path, monkeypatch) -> None:
    m = load_module()
    repo_root = Path(__file__).resolve().parents[2]
    hub = tmp_path / ".gateway" / "hub"
    bridge = tmp_path / ".gateway" / "bridge" / "captain"
    media = tmp_path / "removable"
    key_file = media / ".radriloniuma" / "rootkey" / "architit_root.key"
    response_file = media / ".radriloniuma" / "rootkey" / "challenge_response.sha256"
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key_payload = "architit-root-seed"
    key_file.write_text(key_payload, encoding="utf-8")
    digest = m.sha256_text(key_payload)
    response_file.write_text("bad-response\n", encoding="utf-8")

    hub.mkdir(parents=True, exist_ok=True)
    (hub / "rootkey_pairing.json").write_text(
        json.dumps({"enabled": True, "owner": "architit", "key_id": "AK-004"}, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    (hub / "rootkey_challenge.json").write_text(
        json.dumps({"nonce": "n1", "issued_utc": m.utc_now(), "ttl_sec": 180, "used": False}, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("LAM_HUB_ROOT", str(hub))
    monkeypatch.setenv("LAM_CAPTAIN_BRIDGE_ROOT", str(bridge))
    monkeypatch.setenv("LAM_ROOTKEY_ENABLE", "1")
    monkeypatch.setenv("LAM_ROOTKEY_MEDIA_ROOT", str(media))
    monkeypatch.setenv("LAM_ROOTKEY_ARCHITIT_SHA256", digest)
    monkeypatch.setenv("LAM_ROOTKEY_REQUIRE_CHALLENGE", "1")
    monkeypatch.setenv("LAM_ROOTKEY_FAIL_THRESHOLD", "2")
    monkeypatch.setenv("LAM_ROOTKEY_BAN_SEC", "120")
    monkeypatch.setenv("LAM_ROOTKEY_CHALLENGE_AUTO_ROTATE_SEC", "3600")

    svc = m.RootKeyGate(repo_root)
    p1 = svc.run_once()
    p2 = svc.run_once()
    p3 = svc.run_once()
    assert p1["reason"] == "challenge_response_mismatch"
    assert p2["reason"] in {"challenge_response_mismatch", "challenge_fail_banned"}
    assert p3["reason"] == "challenge_fail_banned"
    assert (hub / "rootkey_challenge_ban.json").exists()
