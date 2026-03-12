from __future__ import annotations

import json
from pathlib import Path

from apps.lam_console.power_fabric_guard import decide_mode
from apps.lam_console.power_fabric_guard import PowerFabricGuard


def test_decide_mode_quiet_hours_overrides_turbo() -> None:
    mode, reasons = decide_mode(
        quiet_active=True,
        load_ratio=0.99,
        swap_used_pct=80.0,
        iowait_pct=30.0,
        gpu_util_pct=95.0,
        fan_rpm_max=3000,
        turbo_load_ratio=0.85,
        turbo_swap_pct=25.0,
        turbo_iowait_pct=12.0,
        quiet_fan_rpm_max=2200,
    )
    assert mode == "quiet_cooling"
    assert "quiet_hours" in reasons


def test_decide_mode_turbo_on_cpu_pressure() -> None:
    mode, reasons = decide_mode(
        quiet_active=False,
        load_ratio=0.9,
        swap_used_pct=10.0,
        iowait_pct=2.0,
        gpu_util_pct=10.0,
        fan_rpm_max=1200,
        turbo_load_ratio=0.85,
        turbo_swap_pct=25.0,
        turbo_iowait_pct=12.0,
        quiet_fan_rpm_max=2200,
    )
    assert mode == "turbo_peak"
    assert "cpu_peak" in reasons


def test_decide_mode_balanced_when_no_pressure() -> None:
    mode, reasons = decide_mode(
        quiet_active=False,
        load_ratio=0.3,
        swap_used_pct=4.0,
        iowait_pct=1.0,
        gpu_util_pct=8.0,
        fan_rpm_max=900,
        turbo_load_ratio=0.85,
        turbo_swap_pct=25.0,
        turbo_iowait_pct=12.0,
        quiet_fan_rpm_max=2200,
    )
    assert mode == "balanced"
    assert "balanced_window" in reasons


def test_manual_profile_override_forces_quiet(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LAM_HUB_ROOT", str(tmp_path / "hub"))
    monkeypatch.setenv("LAM_CAPTAIN_BRIDGE_ROOT", str(tmp_path / "bridge"))
    guard = PowerFabricGuard(Path(__file__).resolve().parents[2])
    (tmp_path / "hub").mkdir(parents=True, exist_ok=True)
    (tmp_path / "hub" / "power_profile.override").write_text("quiet\n", encoding="utf-8")
    payload = guard.run_once()
    assert payload["manual_profile"] == "quiet"
    assert payload["mode"] == "quiet_cooling"
    state = json.loads((tmp_path / "hub" / "power_fabric_state.json").read_text(encoding="utf-8"))
    assert state["mode"] == "quiet_cooling"
