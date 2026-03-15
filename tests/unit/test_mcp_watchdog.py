from __future__ import annotations

from pathlib import Path

from apps.lam_console.mcp_watchdog import MCPWatchdog


def test_watchdog_run_once_no_gemini(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LAM_HUB_ROOT", str(tmp_path / ".gateway" / "hub"))
    monkeypatch.setenv("LAM_CAPTAIN_BRIDGE_ROOT", str(tmp_path / ".gateway" / "bridge" / "captain"))
    monkeypatch.setenv("LAM_MCP_AUTO_HEAL", "0")

    repo_root = Path(__file__).resolve().parents[2]
    watchdog = MCPWatchdog(repo_root)
    monkeypatch.setattr("apps.lam_console.mcp_watchdog.shutil.which", lambda _name: None)

    payload = watchdog.run_once()
    assert payload["health"]["gemini_installed"] is False
    assert (tmp_path / ".gateway" / "hub" / "mcp_watchdog_state.json").exists()


def test_watchdog_forced_heal_calls_sequence(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LAM_HUB_ROOT", str(tmp_path / ".gateway" / "hub"))
    monkeypatch.setenv("LAM_CAPTAIN_BRIDGE_ROOT", str(tmp_path / ".gateway" / "bridge" / "captain"))

    repo_root = Path(__file__).resolve().parents[2]
    watchdog = MCPWatchdog(repo_root)

    monkeypatch.setattr(watchdog, "check_health", lambda: {"overall_ok": False})
    monkeypatch.setattr(watchdog, "heal", lambda: {"ok": True, "post_health": {"overall_ok": True}})

    payload = watchdog.run_once(force_heal=True)
    assert payload["heal_attempted"] is True
    assert payload["heal"]["ok"] is True
