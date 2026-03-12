#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_mem_available_mb() -> int:
    try:
        with Path("/proc/meminfo").open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if line.startswith("MemAvailable:"):
                    parts = line.split()
                    kb = int(parts[1])
                    return kb // 1024
    except Exception:
        return 0
    return 0


def secure_boot_enabled() -> bool:
    try:
        efivar_dir = Path("/sys/firmware/efi/efivars")
        if not efivar_dir.exists():
            return False
        files = list(efivar_dir.glob("SecureBoot-*"))
        if not files:
            return False
        raw = files[0].read_bytes()
        if len(raw) < 5:
            return False
        return raw[4] == 1
    except Exception:
        return False


class SecurityTelemetryGuard:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.hub_root = Path(os.getenv("LAM_HUB_ROOT", str(repo_root / ".gateway" / "hub")))
        self.bridge_root = Path(os.getenv("LAM_CAPTAIN_BRIDGE_ROOT", str(repo_root / ".gateway" / "bridge" / "captain")))
        self.hub_root.mkdir(parents=True, exist_ok=True)
        self.bridge_root.mkdir(parents=True, exist_ok=True)

        self.state_file = self.hub_root / "security_telemetry_state.json"
        self.events_file = self.bridge_root / "events.jsonl"
        self.lockdown_file = self.hub_root / "security_lockdown.flag"
        self.audit_stream_file = self.hub_root / "security_audit_stream.jsonl"

        self.min_disk_gb = int(os.getenv("LAM_SECURITY_MIN_DISK_GB", "5"))
        self.min_mem_mb = int(os.getenv("LAM_SECURITY_MIN_MEM_MB", "512"))
        self.max_load = float(os.getenv("LAM_SECURITY_MAX_LOAD", "32"))
        self.require_secure_boot = os.getenv("LAM_SECURITY_REQUIRE_SECURE_BOOT", "0") in {"1", "true", "True"}
        self.enforce = os.getenv("LAM_SECURITY_ENFORCE", "0") in {"1", "true", "True"}

    @staticmethod
    def _append_event(path: Path, payload: dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=True) + "\n")

    def collect(self) -> dict[str, Any]:
        disk = shutil.disk_usage(self.repo_root)
        free_disk_gb = int(disk.free // (1024**3))
        mem_mb = read_mem_available_mb()

        try:
            load1, load5, load15 = os.getloadavg()
        except OSError:
            load1, load5, load15 = 0.0, 0.0, 0.0

        sb = secure_boot_enabled()

        checks = {
            "disk_ok": free_disk_gb >= self.min_disk_gb,
            "mem_ok": mem_mb >= self.min_mem_mb,
            "load_ok": float(load1) <= self.max_load,
            "secure_boot_ok": (sb if self.require_secure_boot else True),
        }
        overall_ok = all(checks.values())

        payload = {
            "ts_utc": utc_now(),
            "overall_ok": overall_ok,
            "checks": checks,
            "telemetry": {
                "free_disk_gb": free_disk_gb,
                "mem_available_mb": mem_mb,
                "load1": round(float(load1), 3),
                "load5": round(float(load5), 3),
                "load15": round(float(load15), 3),
                "secure_boot_enabled": sb,
            },
            "policy": {
                "min_disk_gb": self.min_disk_gb,
                "min_mem_mb": self.min_mem_mb,
                "max_load": self.max_load,
                "require_secure_boot": self.require_secure_boot,
                "enforce": self.enforce,
            },
        }
        return payload

    def run_once(self) -> dict[str, Any]:
        payload = self.collect()
        self.state_file.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        event = {
            "ts_utc": payload["ts_utc"],
            "event": "security_telemetry_guard",
            "ok": payload["overall_ok"],
            "checks": payload["checks"],
        }
        self._append_event(self.events_file, event)
        self._append_event(
            self.audit_stream_file,
            {"ts_utc": payload["ts_utc"], "source": "security_guard", "event": "security_telemetry_guard", "payload": payload},
        )

        if self.enforce and not payload["overall_ok"]:
            self.lockdown_file.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        elif self.lockdown_file.exists():
            self.lockdown_file.unlink(missing_ok=True)

        return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LAM security telemetry guard.")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval-sec", type=int, default=10)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    guard = SecurityTelemetryGuard(repo_root)

    if args.once:
        print(json.dumps(guard.run_once(), ensure_ascii=True))
        return 0

    while True:
        payload = guard.run_once()
        print(json.dumps({"ts_utc": payload.get("ts_utc"), "overall_ok": payload.get("overall_ok")}, ensure_ascii=True))
        time.sleep(max(2, args.interval_sec))


if __name__ == "__main__":
    raise SystemExit(main())
