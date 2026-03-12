#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_meminfo() -> dict[str, int]:
    out: dict[str, int] = {}
    try:
        with Path("/proc/meminfo").open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                parts = line.split()
                if len(parts) < 2:
                    continue
                key = parts[0].rstrip(":")
                try:
                    out[key] = int(parts[1])
                except ValueError:
                    continue
    except Exception:
        return {}
    return out


def read_fan_rpm_max() -> int | None:
    max_rpm: int | None = None
    for fan_file in Path("/sys/class/hwmon").glob("hwmon*/fan*_input"):
        try:
            rpm = int(fan_file.read_text(encoding="utf-8", errors="replace").strip())
        except Exception:
            continue
        if max_rpm is None or rpm > max_rpm:
            max_rpm = rpm
    return max_rpm


def read_gpu_snapshot() -> dict[str, Any]:
    cmd = shutil.which("nvidia-smi")
    if not cmd:
        return {"available": False}
    try:
        result = subprocess.run(
            [
                cmd,
                "--query-gpu=utilization.gpu,memory.used,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=2.0,
        )
    except Exception:
        return {"available": False}
    if result.returncode != 0:
        return {"available": False}
    line = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
    if not line:
        return {"available": False}
    parts = [x.strip() for x in line.split(",")]
    if len(parts) < 3:
        return {"available": False}
    try:
        return {
            "available": True,
            "util_gpu_pct": float(parts[0]),
            "mem_used_mb": float(parts[1]),
            "temp_c": float(parts[2]),
        }
    except ValueError:
        return {"available": False}


def read_iowait_pct() -> float:
    try:
        with Path("/proc/stat").open("r", encoding="utf-8", errors="replace") as fh:
            first = fh.readline().strip().split()
        if len(first) < 6 or first[0] != "cpu":
            return 0.0
        nums = [int(x) for x in first[1:8]]
        total = float(sum(nums))
        if total <= 0:
            return 0.0
        iowait = float(nums[4])
        return round((iowait / total) * 100.0, 3)
    except Exception:
        return 0.0


def is_quiet_hours(start_hour: int, end_hour: int) -> bool:
    now_hour = datetime.now().hour
    if start_hour == end_hour:
        return False
    if start_hour < end_hour:
        return start_hour <= now_hour < end_hour
    return now_hour >= start_hour or now_hour < end_hour


def decide_mode(
    *,
    quiet_active: bool,
    load_ratio: float,
    swap_used_pct: float,
    iowait_pct: float,
    gpu_util_pct: float | None,
    fan_rpm_max: int | None,
    turbo_load_ratio: float,
    turbo_swap_pct: float,
    turbo_iowait_pct: float,
    quiet_fan_rpm_max: int,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if quiet_active:
        reasons.append("quiet_hours")
        if fan_rpm_max is not None and fan_rpm_max > quiet_fan_rpm_max:
            reasons.append("fan_noise_guard")
        return "quiet_cooling", reasons

    turbo_signal = load_ratio >= turbo_load_ratio or swap_used_pct >= turbo_swap_pct or iowait_pct >= turbo_iowait_pct
    if gpu_util_pct is not None and gpu_util_pct >= 85.0:
        turbo_signal = True
        reasons.append("gpu_peak")
    if turbo_signal:
        if load_ratio >= turbo_load_ratio:
            reasons.append("cpu_peak")
        if swap_used_pct >= turbo_swap_pct:
            reasons.append("swap_pressure")
        if iowait_pct >= turbo_iowait_pct:
            reasons.append("io_wait_pressure")
        return "turbo_peak", reasons

    reasons.append("balanced_window")
    return "balanced", reasons


class PowerFabricGuard:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.hub_root = Path(os.getenv("LAM_HUB_ROOT", str(repo_root / ".gateway" / "hub")))
        self.bridge_root = Path(os.getenv("LAM_CAPTAIN_BRIDGE_ROOT", str(repo_root / ".gateway" / "bridge" / "captain")))
        self.hub_root.mkdir(parents=True, exist_ok=True)
        self.bridge_root.mkdir(parents=True, exist_ok=True)

        self.state_file = self.hub_root / "power_fabric_state.json"
        self.profile_override_file = self.hub_root / "power_profile.override"
        self.events_file = self.bridge_root / "events.jsonl"
        self.audit_stream_file = self.hub_root / "security_audit_stream.jsonl"
        self.noise_guard_file = self.hub_root / "noise_guard.flag"

        self.quiet_start_hour = int(os.getenv("LAM_QUIET_HOURS_START", "22"))
        self.quiet_end_hour = int(os.getenv("LAM_QUIET_HOURS_END", "7"))
        self.quiet_fan_rpm_max = int(os.getenv("LAM_QUIET_FAN_RPM_MAX", "2200"))
        self.turbo_load_ratio = float(os.getenv("LAM_TURBO_LOAD_RATIO", "0.85"))
        self.turbo_swap_pct = float(os.getenv("LAM_TURBO_SWAP_USED_PCT", "25"))
        self.turbo_iowait_pct = float(os.getenv("LAM_TURBO_IOWAIT_PCT", "12"))
        self.enforce_noise_guard = os.getenv("LAM_ENFORCE_NOISE_GUARD", "1") in {"1", "true", "True"}

    @staticmethod
    def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=True) + "\n")

    def _manual_profile(self) -> str:
        env_override = os.getenv("LAM_POWER_PROFILE_OVERRIDE", "").strip().lower()
        if env_override in {"auto", "turbo", "balanced", "quiet"}:
            return env_override
        if self.profile_override_file.exists():
            raw = self.profile_override_file.read_text(encoding="utf-8", errors="replace").strip().lower()
            if raw in {"auto", "turbo", "balanced", "quiet"}:
                return raw
        return "auto"

    def collect(self) -> dict[str, Any]:
        mem = read_meminfo()
        mem_avail_mb = int(mem.get("MemAvailable", 0) // 1024)
        swap_total_kb = int(mem.get("SwapTotal", 0))
        swap_free_kb = int(mem.get("SwapFree", 0))
        swap_used_kb = max(0, swap_total_kb - swap_free_kb)
        swap_used_pct = float((swap_used_kb / swap_total_kb) * 100.0) if swap_total_kb > 0 else 0.0

        try:
            load1, load5, load15 = os.getloadavg()
        except OSError:
            load1, load5, load15 = 0.0, 0.0, 0.0
        cpus = max(1, os.cpu_count() or 1)
        load_ratio = float(load1) / float(cpus)

        gpu = read_gpu_snapshot()
        gpu_util = float(gpu["util_gpu_pct"]) if gpu.get("available") else None
        fan_rpm_max = read_fan_rpm_max()
        iowait_pct = read_iowait_pct()
        quiet_active = is_quiet_hours(self.quiet_start_hour, self.quiet_end_hour)

        mode, reason_codes = decide_mode(
            quiet_active=quiet_active,
            load_ratio=load_ratio,
            swap_used_pct=swap_used_pct,
            iowait_pct=iowait_pct,
            gpu_util_pct=gpu_util,
            fan_rpm_max=fan_rpm_max,
            turbo_load_ratio=self.turbo_load_ratio,
            turbo_swap_pct=self.turbo_swap_pct,
            turbo_iowait_pct=self.turbo_iowait_pct,
            quiet_fan_rpm_max=self.quiet_fan_rpm_max,
        )
        manual_profile = self._manual_profile()
        if manual_profile == "turbo":
            mode = "turbo_peak"
            reason_codes = ["manual_override_turbo"]
        elif manual_profile == "balanced":
            mode = "balanced"
            reason_codes = ["manual_override_balanced"]
        elif manual_profile == "quiet":
            mode = "quiet_cooling"
            reason_codes = ["manual_override_quiet"]

        payload = {
            "ts_utc": utc_now(),
            "mode": mode,
            "manual_profile": manual_profile,
            "reason_codes": reason_codes,
            "quiet_hours_active": quiet_active,
            "telemetry": {
                "cpu_count": cpus,
                "load1": round(float(load1), 3),
                "load5": round(float(load5), 3),
                "load15": round(float(load15), 3),
                "load_ratio": round(float(load_ratio), 3),
                "mem_available_mb": mem_avail_mb,
                "swap_total_mb": int(swap_total_kb // 1024),
                "swap_used_mb": int(swap_used_kb // 1024),
                "swap_used_pct": round(float(swap_used_pct), 3),
                "iowait_pct": round(float(iowait_pct), 3),
                "fan_rpm_max": fan_rpm_max,
                "gpu": gpu,
            },
            "policy": {
                "quiet_start_hour": self.quiet_start_hour,
                "quiet_end_hour": self.quiet_end_hour,
                "quiet_fan_rpm_max": self.quiet_fan_rpm_max,
                "turbo_load_ratio": self.turbo_load_ratio,
                "turbo_swap_pct": self.turbo_swap_pct,
                "turbo_iowait_pct": self.turbo_iowait_pct,
                "enforce_noise_guard": self.enforce_noise_guard,
            },
            "recommendations": {
                "quiet_cooling": [
                    "reduce_background_test_ticks",
                    "prefer_file_gateway_mode",
                    "defer_non_critical_sync_jobs",
                ],
                "turbo_peak": [
                    "allow_high_priority_compute_window",
                    "increase_parallel_queue_jobs",
                    "pin_critical_agents_only",
                ],
                "balanced": [
                    "normal_operation",
                ],
            }.get(mode, []),
        }
        return payload

    def run_once(self) -> dict[str, Any]:
        payload = self.collect()
        self.state_file.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        event = {
            "ts_utc": payload["ts_utc"],
            "event": "power_fabric_guard",
            "mode": payload["mode"],
            "reason_codes": payload["reason_codes"],
        }
        self._append_jsonl(self.events_file, event)
        self._append_jsonl(
            self.audit_stream_file,
            {"ts_utc": payload["ts_utc"], "source": "power_fabric_guard", "event": "power_fabric_guard", "payload": payload},
        )

        quiet_active = bool(payload.get("quiet_hours_active", False))
        fan_rpm = payload.get("telemetry", {}).get("fan_rpm_max")
        noisy = isinstance(fan_rpm, int) and fan_rpm > self.quiet_fan_rpm_max
        if self.enforce_noise_guard and quiet_active and noisy:
            self.noise_guard_file.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        elif self.noise_guard_file.exists():
            self.noise_guard_file.unlink(missing_ok=True)
        return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LAM power fabric guard.")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval-sec", type=int, default=12)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    guard = PowerFabricGuard(repo_root)
    if args.once:
        print(json.dumps(guard.run_once(), ensure_ascii=True))
        return 0
    while True:
        payload = guard.run_once()
        print(json.dumps({"ts_utc": payload.get("ts_utc"), "mode": payload.get("mode")}, ensure_ascii=True))
        time.sleep(max(2, args.interval_sec))


if __name__ == "__main__":
    raise SystemExit(main())
