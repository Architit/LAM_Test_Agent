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
        self.grid_file = self.bridge_root / "ambient_light_grid.json"
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
        
        # Load baseline vector
        vector_payload = self._load_json(self.vector_file, {})
        vector = vector_payload.get("vector", {})
        
        # Load granular grid (Per-Key/Per-LED)
        grid_payload = self._load_json(self.grid_file, {})
        grid = grid_payload.get("grid", {})
        
        # Merge grid into vector if present
        if grid:
            if not isinstance(vector, dict):
                vector = {}
            vector["grid"] = grid
            # If profile is not explicitly set, use per_key_feedback
            if not vector_payload.get("profile"):
                vector_payload["profile"] = "per_key_feedback"

        if not vector and not grid:
            summary = {"ts_utc": utc_now(), "status": "no_vector_or_grid", "dispatched": 0}
            self.state_file.write_text(json.dumps(summary, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
            return summary

        # Calculate hash for deduplication
        combined_payload = {
            "profile": vector_payload.get("profile", "aura_ambient_mirror"),
            "mode": vector_payload.get("mode", "idle"),
            "vector": vector
        }
        raw = json.dumps(combined_payload, ensure_ascii=True, sort_keys=True).encode("utf-8")
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
            
            # If hash is the same and interval is too small, skip
            if prev_hash == vector_hash and (now - prev_ts) < self.min_interval_sec:
                continue
                
            # Construct granular event
            event = {
                "ts_utc": utc_now(),
                "op": "ambient_light_apply",
                "device_id": device_id,
                "profile": combined_payload["profile"],
                "mode": combined_payload["mode"],
                "vector": vector,
                "source": "lam_ambient_light_daemon",
                "hash": vector_hash
            }
            
            # Dispatch to device outbox (both .json and .jsonl for legacy compat)
            outbox_dir = self.bridge_root / "device_outbox" / device_id
            outbox_dir.mkdir(parents=True, exist_ok=True)
            
            # Legacy .jsonl appending
            outbox_file = self.bridge_root / "device_outbox" / f"{device_id}.jsonl"
            self._append_jsonl(outbox_file, event)
            
            # High-fidelity single message
            msg_file = outbox_dir / f"light_{int(now * 1000)}.json"
            msg_file.write_text(json.dumps(event, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
            
            self._append_jsonl(self.events_file, {
                "ts_utc": event["ts_utc"], 
                "event": "ambient_light_dispatched", 
                "device_id": device_id, 
                "has_grid": bool(grid)
            })
            
            last_sent[device_id] = {"hash": vector_hash, "ts_epoch": now, "ts_utc": event["ts_utc"]}
            dispatched += 1

        summary = {
            "ts_utc": utc_now(),
            "status": "ok",
            "dispatched": dispatched,
            "eligible_devices": devices_total,
            "vector_hash": vector_hash,
            "has_grid": bool(grid),
            "last_sent": last_sent,
        }
        
        state_payload = {
            "last_sent": last_sent,
            "last_summary": summary
        }
        self.state_file.write_text(json.dumps(state_payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        
        return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ambient light vector bridge daemon.")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval-sec", type=float, default=2.0)
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
        print(json.dumps({"ts_utc": payload.get("ts_utc"), "dispatched": payload.get("dispatched", 0), "grid": payload.get("has_grid")}, ensure_ascii=True))
        time.sleep(max(0.1, float(args.interval_sec)))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        pass
