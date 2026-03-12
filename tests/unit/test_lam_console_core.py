from __future__ import annotations

import json
from pathlib import Path

from apps.lam_console.core import LocalHubCore


def test_help_command_exposes_console_commands(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LAM_GATEWAY_STATE_DIR", str(tmp_path / ".gateway"))
    core = LocalHubCore(Path(__file__).resolve().parents[2])
    result = core.execute("help")
    assert result.ok is True
    assert "send <agent> <message>" in result.payload["commands"]
    assert "mcp-status" in result.payload["commands"]
    assert "gws-health" in result.payload["commands"]


def test_send_command_writes_agent_inbox_line(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LAM_GATEWAY_STATE_DIR", str(tmp_path / ".gateway"))
    monkeypatch.setenv("LAM_HUB_ROOT", str(tmp_path / ".gateway" / "hub"))
    core = LocalHubCore(Path(__file__).resolve().parents[2])
    result = core.execute("send codex-agent hello world")
    assert result.ok is True
    inbox = Path(result.payload["file"])
    assert inbox.exists()
    lines = inbox.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["agent"] == "codex-agent"
    assert payload["message"] == "hello world"


def test_model_command_spools_when_endpoint_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("LAM_CODEX_ENDPOINT", raising=False)
    monkeypatch.setenv("LAM_GATEWAY_STATE_DIR", str(tmp_path / ".gateway"))
    monkeypatch.setenv("LAM_HUB_ROOT", str(tmp_path / ".gateway" / "hub"))
    core = LocalHubCore(Path(__file__).resolve().parents[2])
    result = core.execute("model codex test-message")
    assert result.ok is False
    assert result.payload["error"] == "endpoint_not_configured"
    spool_file = Path(result.payload["spooled"])
    assert spool_file.exists()
    line = spool_file.read_text(encoding="utf-8").strip().splitlines()[-1]
    payload = json.loads(line)
    assert payload["provider"] == "codex"


def test_open_gate_and_list_gates(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LAM_GATEWAY_STATE_DIR", str(tmp_path / ".gateway"))
    monkeypatch.setenv("LAM_HUB_ROOT", str(tmp_path / ".gateway" / "hub"))
    monkeypatch.setenv("LAM_CAPTAIN_BRIDGE_ROOT", str(tmp_path / ".gateway" / "bridge" / "captain"))
    core = LocalHubCore(Path(__file__).resolve().parents[2])
    result = core.execute("open-gate windows http://127.0.0.1:8765")
    assert result.ok is True
    listed = core.execute("list-gates")
    assert listed.ok is True
    gates = listed.payload["gates"]
    assert any(g.get("target_os") == "windows" for g in gates)


def test_register_and_send_device(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LAM_GATEWAY_STATE_DIR", str(tmp_path / ".gateway"))
    monkeypatch.setenv("LAM_HUB_ROOT", str(tmp_path / ".gateway" / "hub"))
    monkeypatch.setenv("LAM_CAPTAIN_BRIDGE_ROOT", str(tmp_path / ".gateway" / "bridge" / "captain"))
    core = LocalHubCore(Path(__file__).resolve().parents[2])

    reg = core.execute("register-device pixel8 phone android http://127.0.0.1:8765")
    assert reg.ok is True
    listed = core.execute("list-devices")
    assert listed.ok is True
    assert any(d.get("device_id") == "pixel8" for d in listed.payload["devices"])

    snd = core.execute("send-device pixel8 ping from bridge")
    assert snd.ok is True
    outbox = Path(tmp_path / ".gateway" / "bridge" / "captain" / "device_outbox" / "pixel8.jsonl")
    assert outbox.exists()


def test_gws_commands_enqueue_requests(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LAM_GATEWAY_STATE_DIR", str(tmp_path / ".gateway"))
    monkeypatch.setenv("LAM_HUB_ROOT", str(tmp_path / ".gateway" / "hub"))
    monkeypatch.setenv("LAM_CAPTAIN_BRIDGE_ROOT", str(tmp_path / ".gateway" / "bridge" / "captain"))
    core = LocalHubCore(Path(__file__).resolve().parents[2])

    r1 = core.execute("gws-health")
    r2 = core.execute("gws-sync push")
    r3 = core.execute("gws-list docs 5")
    assert r1.ok is True
    assert r2.ok is True
    assert r3.ok is True

    req_file = Path(tmp_path / ".gateway" / "bridge" / "captain" / "gws_requests.jsonl")
    lines = [json.loads(x) for x in req_file.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(lines) == 3
    assert lines[0]["op"] == "health"
    assert lines[1]["op"] == "sync_push"
    assert lines[2]["op"] == "list"


def test_bridge_status_exposes_security_fields(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LAM_GATEWAY_STATE_DIR", str(tmp_path / ".gateway"))
    monkeypatch.setenv("LAM_HUB_ROOT", str(tmp_path / ".gateway" / "hub"))
    monkeypatch.setenv("LAM_CAPTAIN_BRIDGE_ROOT", str(tmp_path / ".gateway" / "bridge" / "captain"))
    core = LocalHubCore(Path(__file__).resolve().parents[2])

    status = core.execute("bridge-status")
    assert status.ok is True
    assert "security_telemetry" in status.payload
    assert "security_lockdown" in status.payload
    assert "role_orchestrator" in status.payload
    assert "power_fabric" in status.payload
    assert "device_mesh" in status.payload
    assert "activity_telemetry" in status.payload
    assert "io_spectral" in status.payload
    assert "governance_autopilot" in status.payload
    assert "media_sync" in status.payload
    assert "rootkey_gate" in status.payload
    assert "failsafe_guard" in status.payload
    assert "feedback_gateway" in status.payload
