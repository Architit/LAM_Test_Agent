# Copyright (c) 2026-06-07 RADRILONIUMA / TRIANIUMA Kingdom. All rights reserved.
import subprocess
import datetime
import sys
from pathlib import Path

# Add global scripts to path
GLOBAL_SCRIPTS = Path(__file__).resolve().parents[1] / "global"
if GLOBAL_SCRIPTS.exists() and str(GLOBAL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(GLOBAL_SCRIPTS))

try:
    from telemetry_shipper import ship_telemetry
except ImportError:
    ship_telemetry = None

DOCUMENT_ID = "1as43exoncCdD4n6MttSLTm2mAszeAxrpeuuSYZ3selA"

def get_systemd_status(unit, user=False):
    try:
        cmd = ["systemctl"]
        if user: cmd.append("--user")
        cmd.extend(["is-active", unit])
        res = subprocess.run(cmd, capture_output=True, text=True)
        return "ONLINE" if res.stdout.strip() == "active" else "OFFLINE"
    except:
        return "ERROR"

def get_mcp_status(name):
    try:
        res = subprocess.run(["gemini", "mcp", "list"], capture_output=True, text=True)
        output = res.stdout + res.stderr
        for line in output.splitlines():
            if name in line and "✓" in line:
                return "CONNECTED"
        return "DISCONNECTED"
    except:
        return "ERROR"

def update_telemetry():
    # Ship buffered events first
    if ship_telemetry:
        try:
            ship_telemetry()
        except Exception as e:
            print(f"[TELEMETRY] Shipper failed: {e}")

    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")
    
    rows = [
        "| Service | Status | Last Ping (UTC) |",
        "|---------|--------|-----------------|"
    ]
    
    # Check services
    rows.append(f"| lam_gateway | {get_systemd_status('lam_gateway.service')} | {now} |")
    rows.append(f"| mcp_bridge | {get_mcp_status('trianiuma-mcp-core')} | {now} |")
    rows.append(f"| queue_worker | {get_systemd_status('lam_queue_worker.timer')} (TIMER) | {now} |")
    rows.append(f"| validating_eye | {get_systemd_status('validating_eye.timer')} (TIMER) | {now} |")
    rows.append(f"| lam_sync | {get_systemd_status('lam_sync.timer')} (TIMER) | {now} |")
    rows.append(f"| chrome_shutdown | {get_systemd_status('chrome-graceful-shutdown.service', user=True)} | {now} |")

    table_content = "\n".join(rows)
    print(">>> Final Telemetry Table:")
    print(table_content)

if __name__ == "__main__":
    update_telemetry()
