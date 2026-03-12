from __future__ import annotations

import json
from pathlib import Path

from apps.lam_console.role_orchestrator import RoleOrchestrator


def test_role_orchestrator_wake_rebind(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LAM_GATEWAY_STATE_DIR", str(tmp_path / ".gateway"))
    monkeypatch.setenv("LAM_HUB_ROOT", str(tmp_path / ".gateway" / "hub"))
    monkeypatch.setenv("LAM_CAPTAIN_BRIDGE_ROOT", str(tmp_path / ".gateway" / "bridge" / "captain"))
    monkeypatch.setenv("LAM_WAKE_DETECT_THRESHOLD_SEC", "1")

    repo_root = Path(__file__).resolve().parents[2]
    orch = RoleOrchestrator(repo_root)
    orch.last_monotonic = 0.0

    payload = orch.run_cycle(monotonic_now=10.0)
    assert "wake" in payload
    assert payload["wake"]["event"] == "device_wake_detected"

    state_file = tmp_path / ".gateway" / "hub" / "role_orchestrator_state.json"
    assert state_file.exists()

    wake_events = tmp_path / ".gateway" / "bridge" / "captain" / "wake_events.jsonl"
    assert wake_events.exists()
    rows = [json.loads(x) for x in wake_events.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert rows[-1]["event"] == "device_wake_detected"


def test_role_orchestrator_lockdown_blocks_role_rebind(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LAM_GATEWAY_STATE_DIR", str(tmp_path / ".gateway"))
    monkeypatch.setenv("LAM_HUB_ROOT", str(tmp_path / ".gateway" / "hub"))
    monkeypatch.setenv("LAM_CAPTAIN_BRIDGE_ROOT", str(tmp_path / ".gateway" / "bridge" / "captain"))
    monkeypatch.setenv("LAM_WAKE_DETECT_THRESHOLD_SEC", "1")

    repo_root = Path(__file__).resolve().parents[2]
    orch = RoleOrchestrator(repo_root)
    (tmp_path / ".gateway" / "hub" / "security_lockdown.flag").write_text("1\n", encoding="utf-8")
    (tmp_path / ".gateway" / "hub" / "role_profile.override").write_text("edge_gateway\n", encoding="utf-8")
    orch.last_monotonic = 0.0

    payload = orch.run_cycle(monotonic_now=10.0)
    assert payload["wake"]["lockdown"] is True
    assert payload["profile"]["name"] == "edge_gateway"
    assert payload["wake"]["roles_notified"] == 0


def test_role_orchestrator_degrades_on_high_load(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LAM_GATEWAY_STATE_DIR", str(tmp_path / ".gateway"))
    monkeypatch.setenv("LAM_HUB_ROOT", str(tmp_path / ".gateway" / "hub"))
    monkeypatch.setenv("LAM_CAPTAIN_BRIDGE_ROOT", str(tmp_path / ".gateway" / "bridge" / "captain"))
    monkeypatch.setenv("LAM_WAKE_DETECT_THRESHOLD_SEC", "1")
    monkeypatch.setenv("LAM_ROLE_MAX_LOAD_BEFORE_DEGRADE", "1")

    repo_root = Path(__file__).resolve().parents[2]
    orch = RoleOrchestrator(repo_root)
    monkeypatch.setattr(orch, "hardware_snapshot", lambda: {"on_ac_power": True, "battery_present": True, "max_temp_c": 50.0, "load1": 10.0})
    orch.last_monotonic = 0.0

    payload = orch.run_cycle(monotonic_now=10.0)
    assert payload["profile"]["name"] == "edge_gateway"
    assert "high_load_degrade" in payload["wake"]["reason_codes"]


def test_role_orchestrator_strict_secure_gate_blocks(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LAM_GATEWAY_STATE_DIR", str(tmp_path / ".gateway"))
    monkeypatch.setenv("LAM_HUB_ROOT", str(tmp_path / ".gateway" / "hub"))
    monkeypatch.setenv("LAM_CAPTAIN_BRIDGE_ROOT", str(tmp_path / ".gateway" / "bridge" / "captain"))
    monkeypatch.setenv("LAM_WAKE_DETECT_THRESHOLD_SEC", "1")
    monkeypatch.setenv("LAM_WAKE_STRICT_SECURE_GATE", "1")

    repo_root = Path(__file__).resolve().parents[2]
    orch = RoleOrchestrator(repo_root)
    monkeypatch.setattr(orch, "secure_posture_ok", lambda: False)
    orch.last_monotonic = 0.0

    payload = orch.run_cycle(monotonic_now=10.0)
    assert payload["wake"]["strict_secure_blocked"] is True
    assert payload["wake"]["roles_notified"] == 0
    assert "strict_secure_gate_blocked" in payload["wake"]["reason_codes"]


def test_role_orchestrator_selector_uses_node_type(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LAM_GATEWAY_STATE_DIR", str(tmp_path / ".gateway"))
    monkeypatch.setenv("LAM_HUB_ROOT", str(tmp_path / ".gateway" / "hub"))
    monkeypatch.setenv("LAM_CAPTAIN_BRIDGE_ROOT", str(tmp_path / ".gateway" / "bridge" / "captain"))
    monkeypatch.setenv("LAM_WAKE_DETECT_THRESHOLD_SEC", "1")
    monkeypatch.setenv("LAM_NODE_TYPE", "server")
    monkeypatch.setenv("LAM_DEVICE_PROFILE", "")

    repo_root = Path(__file__).resolve().parents[2]
    orch = RoleOrchestrator(repo_root)
    orch.last_monotonic = 0.0
    payload = orch.run_cycle(monotonic_now=10.0)
    assert payload["profile"]["name"] == "critical_lifeline"


def test_role_orchestrator_runbook_hold_activation(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LAM_GATEWAY_STATE_DIR", str(tmp_path / ".gateway"))
    monkeypatch.setenv("LAM_HUB_ROOT", str(tmp_path / ".gateway" / "hub"))
    monkeypatch.setenv("LAM_CAPTAIN_BRIDGE_ROOT", str(tmp_path / ".gateway" / "bridge" / "captain"))
    monkeypatch.setenv("LAM_WAKE_DETECT_THRESHOLD_SEC", "1")
    monkeypatch.setenv("LAM_WAKE_STRICT_SECURE_GATE", "1")
    monkeypatch.setenv("LAM_ROLE_REASON_HOLD_THRESHOLD", "1")

    repo_root = Path(__file__).resolve().parents[2]
    orch = RoleOrchestrator(repo_root)
    monkeypatch.setattr(orch, "secure_posture_ok", lambda: False)
    orch.last_monotonic = 0.0

    payload = orch.run_cycle(monotonic_now=10.0)
    assert payload["runbook"]["hold_activated"] is True
    assert (tmp_path / ".gateway" / "hub" / "role_orchestrator_hold.flag").exists()
