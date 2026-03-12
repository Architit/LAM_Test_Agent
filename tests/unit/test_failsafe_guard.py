from __future__ import annotations

import json
from pathlib import Path

from apps.lam_console.failsafe_guard import FailsafeGuard


def test_failsafe_activates_after_threshold(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LAM_GATEWAY_STATE_DIR", str(tmp_path / ".gateway"))
    monkeypatch.setenv("LAM_HUB_ROOT", str(tmp_path / ".gateway" / "hub"))
    monkeypatch.setenv("LAM_CAPTAIN_BRIDGE_ROOT", str(tmp_path / ".gateway" / "bridge" / "captain"))
    monkeypatch.setenv("LAM_FAILSAFE_ACTIVATE_AFTER_CYCLES", "2")
    monkeypatch.setenv("LAM_FAILSAFE_RECOVER_AFTER_CYCLES", "3")

    repo_root = Path(__file__).resolve().parents[2]
    guard = FailsafeGuard(repo_root)

    sec = tmp_path / ".gateway" / "hub" / "security_telemetry_state.json"
    sec.parent.mkdir(parents=True, exist_ok=True)
    sec.write_text(json.dumps({"overall_ok": False, "checks": {"disk_ok": False}}, ensure_ascii=True), encoding="utf-8")

    p1 = guard.run_once()
    assert p1["active"] is False
    p2 = guard.run_once()
    assert p2["active"] is True
    assert (tmp_path / ".gateway" / "hub" / "failsafe_active.flag").exists()
    assert (tmp_path / ".gateway" / "hub" / "role_profile.override").read_text(encoding="utf-8").strip() == "critical_lifeline"

    policy_file = tmp_path / ".gateway" / "routing_policy.json"
    policy = json.loads(policy_file.read_text(encoding="utf-8"))
    assert policy.get("data_circulation", {}).get("kill_switch") is True


def test_failsafe_auto_recovers_after_stable_cycles(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LAM_GATEWAY_STATE_DIR", str(tmp_path / ".gateway"))
    monkeypatch.setenv("LAM_HUB_ROOT", str(tmp_path / ".gateway" / "hub"))
    monkeypatch.setenv("LAM_CAPTAIN_BRIDGE_ROOT", str(tmp_path / ".gateway" / "bridge" / "captain"))
    monkeypatch.setenv("LAM_FAILSAFE_ACTIVATE_AFTER_CYCLES", "1")
    monkeypatch.setenv("LAM_FAILSAFE_RECOVER_AFTER_CYCLES", "2")
    monkeypatch.setenv("LAM_FAILSAFE_AUTO_RECOVER", "1")

    repo_root = Path(__file__).resolve().parents[2]
    guard = FailsafeGuard(repo_root)
    sec = tmp_path / ".gateway" / "hub" / "security_telemetry_state.json"
    sec.parent.mkdir(parents=True, exist_ok=True)

    sec.write_text(json.dumps({"overall_ok": False}, ensure_ascii=True), encoding="utf-8")
    p1 = guard.run_once()
    assert p1["active"] is True

    sec.write_text(json.dumps({"overall_ok": True}, ensure_ascii=True), encoding="utf-8")
    p2 = guard.run_once()
    assert p2["active"] is True
    p3 = guard.run_once()
    assert p3["active"] is False
    assert not (tmp_path / ".gateway" / "hub" / "failsafe_active.flag").exists()

    policy_file = tmp_path / ".gateway" / "routing_policy.json"
    policy = json.loads(policy_file.read_text(encoding="utf-8"))
    assert policy.get("data_circulation", {}).get("kill_switch") is False

