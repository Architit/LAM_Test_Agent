#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class AmbientLightBridge:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.hub_root = Path(os.getenv("LAM_HUB_ROOT", str(repo_root / ".gateway" / "hub")))
        self.bridge_root = Path(os.getenv("LAM_CAPTAIN_BRIDGE_ROOT", str(repo_root / ".gateway" / "bridge" / "captain")))
        self.hub_root.mkdir(parents=True, exist_ok=True)
        self.bridge_root.mkdir(parents=True, exist_ok=True)
        (self.bridge_root / "device_outbox").mkdir(parents=True, exist_ok=True)

        self.devices_file = self.bridge_root / "devices.json"
        self.vector_file = self.bridge_root / "ambient_light_vector.json"
        self.events_file = self.bridge_root / "events.jsonl"
        self.state_file = self.hub_root / "ambient_light_state.json"
        self.min_interval_sec = float(os.getenv("LAM_AMBIENT_DISPATCH_MIN_INTERVAL_SEC", "0.20"))

    @staticmethod
    def _load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
        if not path.exists():
            return default
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return default
        return payload if isinstance(payload, dict) else default

    @staticmethod
    def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=True) + "\n")

    def _load_devices(self) -> list[dict[str, Any]]:
        payload = self._load_json(self.devices_file, {"devices": []})
        devices = payload.get("devices", [])
        return [d for d in devices if isinstance(d, dict)]

    @staticmethod
    def _device_allowed(device: dict[str, Any]) -> bool:
        consent = device.get("consent", {})
        if not isinstance(consent, dict) or not consent.get("approved"):
            return False
        scopes = [str(x) for x in device.get("scopes", []) if isinstance(x, str)]
        trust = str(device.get("trust_level", "discovery"))
        if "ambient_light" in scopes:
            return True
        return "full_data_access" in scopes and trust == "verified_full"

    def run_once(self) -> dict[str, Any]:
        state = self._load_json(self.state_file, {"last_sent": {}})
        vector_payload = self._load_json(self.vector_file, {})
        vector = vector_payload.get("vector", {}) if isinstance(vector_payload, dict) else {}
        if not isinstance(vector, dict) or not vector:
            summary = {"ts_utc": utc_now(), "status": "no_vector", "dispatched": 0}
            self.state_file.write_text(json.dumps(summary, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
            return summary

        raw = json.dumps(vector_payload, ensure_ascii=True, sort_keys=True).encode("utf-8")
        vector_hash = hashlib.sha256(raw).hexdigest()[:16]
        now = time.time()

        last_sent = state.get("last_sent", {})
        if not isinstance(last_sent, dict):
            last_sent = {}
        dispatched = 0
        devices_total = 0
        for device in self._load_devices():
            if not self._device_allowed(device):
                continue
            device_id = str(device.get("device_id", "")).strip().lower()
            if not device_id:
                continue
            devices_total += 1
            prev = last_sent.get(device_id, {})
            prev_hash = str(prev.get("hash", ""))
            prev_ts = float(prev.get("ts_epoch", 0.0))
            if prev_hash == vector_hash and (now - prev_ts) < self.min_interval_sec:
                continue
            event = {
                "ts_utc": utc_now(),
                "op": "ambient_light_apply",
                "device_id": device_id,
                "profile": vector_payload.get("profile", "aura_ambient_mirror"),
                "mode": vector_payload.get("mode", "idle"),
                "pane": vector_payload.get("pane", ""),
                "mirror_pane": vector_payload.get("mirror_pane", ""),
                "vector": vector,
                "source": "lam_ambient_light_daemon",
            }
            outbox = self.bridge_root / "device_outbox" / f"{device_id}.jsonl"
            self._append_jsonl(outbox, event)
            self._append_jsonl(self.events_file, {"ts_utc": event["ts_utc"], "event": "ambient_light_dispatched", "device_id": device_id, "mode": event["mode"]})
            last_sent[device_id] = {"hash": vector_hash, "ts_epoch": now, "ts_utc": event["ts_utc"]}
            dispatched += 1

        summary = {
            "ts_utc": utc_now(),
            "status": "ok",
            "dispatched": dispatched,
            "eligible_devices": devices_total,
            "vector_hash": vector_hash,
            "vector_mode": vector_payload.get("mode", "idle"),
            "profile": vector_payload.get("profile", "aura_ambient_mirror"),
            "last_sent": last_sent,
        }
        self.state_file.write_text(json.dumps(summary, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ambient light vector bridge daemon.")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval-sec", type=int, default=2)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    svc = AmbientLightBridge(repo_root)
    if args.once:
        print(json.dumps(svc.run_once(), ensure_ascii=True))
        return 0
    while True:
        payload = svc.run_once()
        print(json.dumps({"ts_utc": payload.get("ts_utc"), "dispatched": payload.get("dispatched", 0)}, ensure_ascii=True))
        time.sleep(max(1, int(args.interval_sec)))


if __name__ == "__main__":
    raise SystemExit(main())
