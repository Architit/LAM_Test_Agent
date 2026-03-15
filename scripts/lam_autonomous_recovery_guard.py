#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

class AutonomousRecoveryGuard:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.hub_root = Path(os.getenv("LAM_HUB_ROOT", str(repo_root / ".gateway" / "hub")))
        self.bridge_root = Path(os.getenv("LAM_CAPTAIN_BRIDGE_ROOT", str(repo_root / ".gateway" / "bridge" / "captain")))
        self.pid_dir = Path(os.getenv("LAM_STACK_PID_DIR", str(repo_root / ".gateway" / "hub" / "pids")))
        
        self.hub_root.mkdir(parents=True, exist_ok=True)
        self.bridge_root.mkdir(parents=True, exist_ok=True)
        self.pid_dir.mkdir(parents=True, exist_ok=True)
        
        self.state_file = self.hub_root / "autonomous_recovery_state.json"
        self.events_file = self.bridge_root / "events.jsonl"
        
        # All directories monitoring
        self.heartbeat_dirs = [
            repo_root / "data" / "local" / "transit" / "neutral_layer" / "core",
            repo_root / "data" / "local" / "transit" / "neutral_layer",
            repo_root / "memory" / "ARIERGARD_MEM_CORE" / "2026"
        ]
        
        # Critical processes to keep alive
        self.critical_processes = {
            "mcp_watchdog": repo_root / "scripts" / "lam_mcp_watchdog.sh",
            "realtime_circulation": repo_root / "scripts" / "lam_realtime_circulation.sh",
            "media_sync": repo_root / "scripts" / "lam_media_sync.sh",
            "governance_autopilot": repo_root / "scripts" / "lam_governance_autopilot.sh",
            "failsafe_guard": repo_root / "scripts" / "lam_failsafe_guard.sh"
        }

    def _log_event(self, event: str, payload: dict[str, Any]) -> None:
        row = {"ts_utc": utc_now(), "event": event, **payload}
        with self.events_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=True) + "\n")

    def check_process_alive(self, name: str) -> bool:
        pid_file = self.pid_dir / f"{name}.pid"
        if not pid_file.exists():
            return False
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 0)
            return True
        except (ValueError, OSError):
            return False

    def restart_process(self, name: str, script_path: Path) -> bool:
        self._log_event("autonomous_recovery_restarting_process", {"process": name})
        stack_script = self.repo_root / "scripts" / "lam_bridge_stack.sh"
        try:
            # We use the bridge stack to start it properly with nohup/env
            # This avoids duplicating environment setup logic
            subprocess.run([str(stack_script), "start"], check=False)
            return True
        except Exception as e:
            self._log_event("process_restart_error", {"process": name, "error": str(e)})
            return False

    def check_and_heal_mcp(self) -> dict[str, Any]:
        watchdog_script = self.repo_root / "scripts" / "lam_mcp_watchdog.sh"
        if not watchdog_script.exists():
            return {"ok": False, "reason": "watchdog_script_missing"}
        try:
            res = subprocess.run([str(watchdog_script), "--once"], capture_output=True, text=True, check=False)
            data = json.loads(res.stdout)
            if data.get("health", {}).get("overall_ok"):
                return {"ok": True, "action": "none"}
            
            self._log_event("autonomous_recovery_healing_mcp", {"reason": "transport_down"})
            res = subprocess.run([str(watchdog_script), "--once", "--heal-now"], capture_output=True, text=True, check=False)
            return {"ok": True, "action": "healed", "details": json.loads(res.stdout)}
        except Exception as e:
            return {"ok": False, "reason": str(e)}

    def refresh_all_heartbeats(self) -> None:
        now_date = datetime.now().strftime('%Y-%m-%d')
        for base_dir in self.heartbeat_dirs:
            if not base_dir.exists(): continue
            for hb_file in base_dir.rglob("HEARTBEAT.md"):
                try:
                    content = hb_file.read_text(encoding="utf-8")
                    lines = content.splitlines()
                    updated = False
                    for i, line in enumerate(lines):
                        if "HEARTBEAT" in line:
                            lines[i] = f"# HEARTBEAT ({now_date}) ⚜️"
                            updated = True
                    if updated:
                        hb_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
                except Exception as e:
                    self._log_event("heartbeat_refresh_error", {"file": str(hb_file), "error": str(e)})

    def full_forest_pulse(self) -> None:
        """Triggers a circulation cycle and aggregates global heartbeat reports."""
        circulation_script = self.repo_root / "scripts" / "lam_realtime_circulation.sh"
        if circulation_script.exists():
            subprocess.run([str(circulation_script), "--once"], check=False)
            self._log_event("autonomous_recovery_forest_pulse", {"status": "dispatched"})
        
        # Sync Export Pipes (WSL -> Windows C:\data)
        export_script = self.repo_root / "scripts" / "lam_export_pipe_sync.sh"
        if export_script.exists():
            subprocess.run([str(export_script)], check=False)
            self._log_event("autonomous_recovery_export_sync", {"status": "completed"})

        # Aggregate global report
        self._aggregate_global_report()

    def _aggregate_global_report(self) -> None:
        """Collects status from all organs and updates GLOBAL_HEARTBEAT_REPORT.md."""
        report_path = self.repo_root.parent / "RADRILONIUMA" / "data" / "local" / "transit" / "neutral_layer" / "GLOBAL_HEARTBEAT_REPORT.md"
        if not report_path.parent.exists():
            report_path.parent.mkdir(parents=True, exist_ok=True)
            
        timestamp = utc_now()
        report = [
            "# GLOBAL HEARTBEAT REPORT: THE SOVEREIGN FOREST",
            f"timestamp_utc: {timestamp}",
            "",
            "| Organ | State | Pulse | Last Sync |",
            "|-------|-------|-------|-----------|"
        ]
        
        for organ_dir in self.repo_root.parent.iterdir():
            if not organ_dir.is_dir() or organ_dir.name.startswith(".") or organ_dir.name in ["data", "lam-wheelhouse"]:
                continue
            
            hb_file = organ_dir / "data" / "local" / "transit" / "neutral_layer" / "core" / organ_dir.name / "HEARTBEAT.md"
            if not hb_file.exists():
                hb_file = organ_dir / "data" / "local" / "transit" / "neutral_layer" / "HEARTBEAT.md"
            
            state = "DORMANT"
            pulse = "UNKNOWN"
            last_sync = "NEVER"
            
            if hb_file.exists():
                content = hb_file.read_text(encoding="utf-8")
                state = "ACTIVE" if "ACTIVE" in content or "OFFLINE_PRIMARY" in content else "DORMANT"
                pulse = "STABLE" if "STABLE" in content or "SYNCED" in content else "WEAK"
                mtime = datetime.fromtimestamp(hb_file.stat().st_mtime, tz=timezone.utc)
                last_sync = mtime.strftime("%Y-%m-%dT%H:%M:%SZ")
            
            report.append(f"| {organ_dir.name} | {state} | {pulse} | {last_sync} |")
            
        report_path.write_text("\n".join(report) + "\n", encoding="utf-8")
        self._log_event("global_report_aggregated", {"path": str(report_path)})

    def run_cycle(self) -> None:
        # 1. Check MCP
        mcp_status = self.check_and_heal_mcp()
        
        # 2. Check stack health
        process_stats = {}
        for name, path in self.critical_processes.items():
            alive = self.check_process_alive(name)
            process_stats[name] = "alive" if alive else "dead"
            if not alive:
                self.restart_process(name, path)
        
        # 3. Refresh heartbeats
        self.refresh_all_heartbeats()
        
        # 4. Trigger circulation
        self.full_forest_pulse()
        
        state = {
            "ts_utc": utc_now(),
            "mcp_status": mcp_status,
            "processes": process_stats,
            "mode": os.getenv("LAM_GATEWAY_OFFLINE_PRIMARY", "0")
        }
        self.state_file.write_text(json.dumps(state, indent=2) + "\n")
        self._log_event("autonomous_recovery_cycle", state)

if __name__ == "__main__":
    repo = Path(__file__).resolve().parents[1]
    guard = AutonomousRecoveryGuard(repo)
    # Background loop
    while True:
        guard.run_cycle()
        time.sleep(300) 
