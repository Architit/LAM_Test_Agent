#!/usr/bin/env python3
from __future__ import annotations

import curses
import json
import os
import sys
import time
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# Paths
ROOT = Path(os.getenv("LAM_REPO_ROOT", Path(__file__).resolve().parents[2]))
EVENTS_FILE = ROOT / ".gateway" / "bridge" / "captain" / "events.jsonl"
HEARTBEAT_REPORT = ROOT.parent / "RADRILONIUMA" / "data" / "local" / "transit" / "neutral_layer" / "GLOBAL_HEARTBEAT_REPORT.md"
AUTONOMOUS_STATE = ROOT / ".gateway" / "hub" / "autonomous_recovery_state.json"

ORGANS = [
    "Aristos", "Ayaearias-Triania", "Croambeth", "Fomanor", "Glokha", "Jouna",
    "Kitora", "Larpat", "Luvia", "Melia", "Oxin", "Pralia", "Sataris", "Taspit",
    "Vilami", "Vionori", "Vrela", "Zudory", "RADRILONIUMA-PROJECT", "CORE",
    "LAM", "Archivator_Agent", "Trianiuma", "System-"
]

class RadriloniumaOS:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)     # Title
        curses.init_pair(2, curses.COLOR_GREEN, -1)    # Online / OK
        curses.init_pair(3, curses.COLOR_RED, -1)      # Offline / Error
        curses.init_pair(4, curses.COLOR_YELLOW, -1)   # Syncing / Warning
        curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Header bar
        curses.init_pair(6, curses.COLOR_MAGENTA, -1)  # Special accents
        
        self.stdscr.nodelay(True)
        curses.curs_set(0)
        self.running = True
        self.logs = []
        
        # Read initial events to prepopulate log
        self._read_logs()

    def _read_logs(self):
        if EVENTS_FILE.exists():
            try:
                lines = EVENTS_FILE.read_text(encoding="utf-8").strip().splitlines()
                # Get last 20 lines
                self.logs = []
                for line in lines[-20:]:
                    try:
                        data = json.loads(line)
                        ts = data.get("ts_utc", "")[11:19]
                        evt = data.get("event", "unknown")
                        self.logs.append(f"[{ts}] {evt}")
                    except json.JSONDecodeError:
                        self.logs.append(line[:100])
            except Exception:
                pass

    def _get_organ_states(self):
        states = {}
        for organ in ORGANS:
            organ_path = ROOT.parent / organ
            if organ_path.exists():
                hb = organ_path / "data" / "local" / "transit" / "neutral_layer" / "core" / organ / "HEARTBEAT.md"
                if not hb.exists():
                    hb = organ_path / "data" / "local" / "transit" / "neutral_layer" / "HEARTBEAT.md"
                if hb.exists():
                    try:
                        content = hb.read_text(encoding="utf-8")
                        if "ACTIVE" in content or "OFFLINE_PRIMARY" in content:
                            states[organ] = "ONLINE"
                        else:
                            states[organ] = "DORMANT"
                    except Exception:
                        states[organ] = "ERROR"
                else:
                    states[organ] = "NO_PULSE"
            else:
                states[organ] = "MISSING"
        return states

    def _get_sys_metrics(self):
        # Memory
        mem_total, mem_avail = 0, 0
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        mem_total = int(line.split()[1])
                    elif line.startswith('MemAvailable:'):
                        mem_avail = int(line.split()[1])
        except Exception:
            pass
        mem_used_pct = ((mem_total - mem_avail) / mem_total * 100) if mem_total else 0
        
        # Load
        try:
            load = os.getloadavg()
        except Exception:
            load = (0.0, 0.0, 0.0)
            
        return {
            "load": load,
            "mem_pct": mem_used_pct
        }

    def safe_addstr(self, y, x, string, attr=0):
        try:
            max_y, max_x = self.stdscr.getmaxyx()
            if y < 0 or y >= max_y or x < 0 or x >= max_x:
                return
            # Truncate string if it would exceed the current line
            available_width = max_x - x
            if len(string) > available_width:
                string = string[:available_width-1]
            
            # Use insstr for the bottom-right corner case
            if y == max_y - 1 and x + len(string) >= max_x:
                self.stdscr.insstr(y, x, string, attr)
            else:
                self.stdscr.addstr(y, x, string, attr)
        except curses.error:
            pass

    def draw_header(self, max_y, max_x):
        header_text = " RADRILONIUMA OS | GLOBAL ADMINISTRATOR CONSOLE ⚜️ "
        time_text = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        self.stdscr.attron(curses.color_pair(5))
        self.stdscr.addstr(0, 0, " " * max_x)
        self.safe_addstr(0, 2, header_text)
        self.safe_addstr(0, max_x - len(time_text) - 2, time_text)
        self.stdscr.attroff(curses.color_pair(5))

    def draw_organs(self, max_y, max_x):
        # Left panel: Organs
        self.stdscr.attron(curses.color_pair(1))
        self.safe_addstr(2, 2, "┌─ SOVEREIGN TREES (ORGANS) ───────────────┐")
        for i in range(3, max_y - 12):
            self.safe_addstr(i, 2, "│                                          │")
        self.safe_addstr(max_y - 12, 2, "└──────────────────────────────────────────┘")
        self.stdscr.attroff(curses.color_pair(1))

        states = self._get_organ_states()
        row = 3
        col = 4
        for i, organ in enumerate(ORGANS):
            if row >= max_y - 13:
                break
            
            state = states.get(organ, "UNKNOWN")
            color = curses.color_pair(2) if state == "ONLINE" else (curses.color_pair(4) if state in ["DORMANT", "NO_PULSE"] else curses.color_pair(3))
            
            # Truncate long names
            display_name = (organ[:18] + '..') if len(organ) > 20 else organ
            self.safe_addstr(row, col, f"■ {display_name:<20}", curses.color_pair(1))
            self.safe_addstr(row, col + 24, f"[{state:<8}]", color)
            row += 1

    def draw_telemetry(self, max_y, max_x):
        # Middle panel
        if max_x < 90: return
        start_x = 48
        width = max_x - start_x - 2
        
        self.stdscr.attron(curses.color_pair(1))
        self.safe_addstr(2, start_x, "┌─ GLOBAL TELEMETRY & STATUS " + "─" * (width - 29) + "┐")
        for i in range(3, 12):
            self.safe_addstr(i, start_x, "│" + " " * (width - 2) + "│")
        self.safe_addstr(12, start_x, "└" + "─" * (width - 2) + "┘")
        self.stdscr.attroff(curses.color_pair(1))
        
        metrics = self._get_sys_metrics()
        load_str = f"{metrics['load'][0]:.2f}, {metrics['load'][1]:.2f}, {metrics['load'][2]:.2f}"
        mem_str = f"{metrics['mem_pct']:.1f}%"
        
        auto_state = "UNKNOWN"
        mcp_state = "UNKNOWN"
        if AUTONOMOUS_STATE.exists():
            try:
                st = json.loads(AUTONOMOUS_STATE.read_text())
                auto_state = "ACTIVE" if str(st.get("mode")) == "1" else "STANDBY"
                mcp_status = st.get("mcp_status", {})
                if isinstance(mcp_status, dict):
                    mcp_state = "OK" if mcp_status.get("ok") else "FAIL"
            except Exception:
                pass

        self.safe_addstr(4, start_x + 2, "SYSTEM LOAD: ", curses.color_pair(1))
        self.safe_addstr(4, start_x + 20, load_str, curses.color_pair(2) if metrics['load'][0] < 4 else curses.color_pair(3))
        
        self.safe_addstr(5, start_x + 2, "MEMORY USAGE: ", curses.color_pair(1))
        self.safe_addstr(5, start_x + 20, mem_str, curses.color_pair(2) if metrics['mem_pct'] < 80 else curses.color_pair(3))

        self.safe_addstr(7, start_x + 2, "AUTOPILOT: ", curses.color_pair(1))
        self.safe_addstr(7, start_x + 20, auto_state, curses.color_pair(2) if auto_state == "ACTIVE" else curses.color_pair(4))

        self.safe_addstr(8, start_x + 2, "MCP TRANSPORT: ", curses.color_pair(1))
        self.safe_addstr(8, start_x + 20, mcp_state, curses.color_pair(2) if mcp_state == "OK" else curses.color_pair(3))

    def draw_logs(self, max_y, max_x):
        # Bottom panel
        start_y = max_y - 11
        self.stdscr.attron(curses.color_pair(1))
        self.safe_addstr(start_y, 2, "┌─ TERMINAL EVENTS ──────────" + "─" * (max_x - 33) + "┐")
        for i in range(start_y + 1, max_y - 2):
            self.safe_addstr(i, 2, "│" + " " * (max_x - 5) + "│")
        self.safe_addstr(max_y - 2, 2, "└" + "─" * (max_x - 5) + "┘")
        self.stdscr.attroff(curses.color_pair(1))
        
        self._read_logs()
        log_capacity = max_y - start_y - 3
        if log_capacity > 0:
            display_logs = self.logs[-log_capacity:]
            for idx, line in enumerate(display_logs):
                self.safe_addstr(start_y + 1 + idx, 4, line, curses.color_pair(6))

    def draw_footer(self, max_y, max_x):
        footer_text = " [Q]uit | [F]orce Sync | [R]efresh "
        self.stdscr.attron(curses.color_pair(5))
        # Use insstr for background to avoid cursor wrap error on bottom-right corner
        try:
            self.stdscr.move(max_y - 1, 0)
            self.stdscr.insstr(" " * max_x)
        except curses.error:
            pass
        self.safe_addstr(max_y - 1, 2, footer_text)
        self.stdscr.attroff(curses.color_pair(5))

    def run(self):
        while self.running:
            self.stdscr.erase()
            max_y, max_x = self.stdscr.getmaxyx()
            
            if max_y < 20 or max_x < 80:
                self.safe_addstr(0, 0, "Terminal too small. Please resize.")
            else:
                self.draw_header(max_y, max_x)
                self.draw_organs(max_y, max_x)
                self.draw_telemetry(max_y, max_x)
                self.draw_logs(max_y, max_x)
                self.draw_footer(max_y, max_x)
                
            self.stdscr.refresh()
            
            # Handle input non-blocking
            try:
                c = self.stdscr.getch()
                if c != -1:
                    if c in [ord('q'), ord('Q')]:
                        self.running = False
                    elif c in [ord('r'), ord('R')]:
                        self._read_logs()
                    elif c in [ord('f'), ord('F')]:
                        subprocess.run([str(ROOT / "scripts" / "lam_realtime_circulation.sh"), "--once"], check=False)
            except curses.error:
                pass
                
            time.sleep(1)

def main(stdscr):
    os_ui = RadriloniumaOS(stdscr)
    os_ui.run()

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
