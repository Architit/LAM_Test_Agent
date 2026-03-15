#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class FeedbackEngine:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.bridge_root = Path(os.getenv("LAM_CAPTAIN_BRIDGE_ROOT", str(repo_root / ".gateway" / "bridge" / "captain")))
        self.events_file = self.bridge_root / "events.jsonl"
        self.grid_file = self.bridge_root / "ambient_light_grid.json"
        self.last_pos = 0
        
        # Initial grid state
        self.grid: dict[str, list[int]] = {
            "key_f": [0, 0, 40],   # Failsafe
            "key_s": [0, 40, 0],   # Security
            "key_p": [40, 40, 0],  # Power
            "key_r": [40, 0, 0],   # Rootkey
            "key_m": [0, 40, 40],  # Media
        }

    def _update_grid_file(self) -> None:
        payload = {
            "ts_utc": utc_now(),
            "profile": "per_key_feedback",
            "grid": self.grid
        }
        self.grid_file.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

    def process_event(self, event: dict[str, Any]) -> None:
        evt_type = event.get("event", "unknown")
        
        if evt_type == "security_telemetry_guard":
            ok = event.get("ok", False)
            self.grid["key_s"] = [0, 255, 0] if ok else [255, 0, 0]
            
        elif evt_type == "failsafe_cycle":
            active = event.get("active", False)
            self.grid["key_f"] = [255, 0, 0] if active else [0, 0, 255]
            
        elif evt_type == "power_fabric_guard":
            mode = event.get("mode", "unknown")
            if mode == "performance":
                self.grid["key_p"] = [255, 255, 255]
            elif mode == "balanced":
                self.grid["key_p"] = [0, 255, 255]
            else:
                self.grid["key_p"] = [255, 128, 0]
                
        elif evt_type == "rootkey_gate_cycle":
            active = event.get("active", False)
            self.grid["key_r"] = [255, 0, 255] if active else [60, 0, 60]

        elif evt_type == "media_stream_sync_tick":
            self.grid["key_m"] = [255, 255, 255] # Flash white
            self._update_grid_file()
            time.sleep(0.1)
            self.grid["key_m"] = [0, 100, 100] # Back to cyan

        self._update_grid_file()

    def run_loop(self) -> None:
        if self.events_file.exists():
            self.last_pos = self.events_file.stat().st_size
            
        print(f"Feedback Engine started. Monitoring {self.events_file}")
        self._update_grid_file()

        while True:
            if not self.events_file.exists():
                time.sleep(1)
                continue
                
            curr_size = self.events_file.stat().st_size
            if curr_size < self.last_pos: # File rotated
                self.last_pos = 0
                
            if curr_size > self.last_pos:
                with self.events_file.open("r", encoding="utf-8") as f:
                    f.seek(self.last_pos)
                    for line in f:
                        try:
                            event = json.loads(line)
                            self.process_event(event)
                        except json.JSONDecodeError:
                            continue
                    self.last_pos = f.tell()
            
            time.sleep(0.5)


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[2]
    engine = FeedbackEngine(repo_root)
    try:
        engine.run_loop()
    except KeyboardInterrupt:
        pass
