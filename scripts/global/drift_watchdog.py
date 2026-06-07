# Copyright (c) 2026-06-07 RADRILONIUMA / TRIANIUMA Kingdom. All rights reserved.
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

# Canonical Source Config
REPO_RAW_BASE = "https://raw.githubusercontent.com/Architit/RADRILONIUMA/master"
CRITICAL_FILES = {
    "LICENSE.md": f"{REPO_RAW_BASE}/LICENSE.md",
    "NOTICE.md": f"{REPO_RAW_BASE}/NOTICE.md",
    "devkit/patch.sh": f"{REPO_RAW_BASE}/devkit/patch.sh",
    "scripts/global/telemetry_shipper.py": f"{REPO_RAW_BASE}/scripts/global/telemetry_shipper.py",
}

def get_sha256(path: Path) -> str:
    if not path.exists():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()

def log_heal_event(file_path, status, msg):
    """Log event to the local telemetry buffer."""
    event = {
        "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "event": "roaudter.heal",
        "file": str(file_path),
        "status": status,
        "msg": msg
    }
    buffer_file = Path(".gateway/telemetry_events.jsonl")
    buffer_file.parent.mkdir(parents=True, exist_ok=True)
    with buffer_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")

def run_watchdog():
    """Checks for drift and heals critical files."""
    print(">>> [WATCHDOG] Initiating Healing Scan...")
    healed_count = 0
    
    for rel_path, url in CRITICAL_FILES.items():
        local_path = Path(rel_path)
        if not local_path.parent.exists():
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
        try:
            # Fetch remote content
            with urllib.request.urlopen(url, timeout=10) as response:
                remote_content = response.read()
            
            remote_sha = hashlib.sha256(remote_content).hexdigest()
            local_sha = get_sha256(local_path)
            
            if local_sha != remote_sha:
                print(f"[WATCHDOG] Drift detected: {rel_path}. Healing...")
                local_path.write_bytes(remote_content)
                log_heal_event(rel_path, "SUCCESS", f"Restored from {url}")
                healed_count += 1
            else:
                # print(f"[WATCHDOG] {rel_path} is resonant.")
                pass
                
        except Exception as e:
            print(f"[WATCHDOG] Error checking {rel_path}: {e}")
            log_heal_event(rel_path, "ERROR", str(e))
            
    if healed_count > 0:
        print(f">>> [WATCHDOG] Healing COMPLETE. {healed_count} files restored.")
    else:
        print(">>> [WATCHDOG] Scan COMPLETE. System is resonant.")

if __name__ == "__main__":
    run_watchdog()
