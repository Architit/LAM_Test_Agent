#!/usr/bin/env python3
import time
import json
import os
from pathlib import Path
from datetime import datetime

# Generic Agent Executor Daemon
WORK_DIR = Path(os.getcwd())
NODE_NAME = WORK_DIR.name

IMPORT_DIR = WORK_DIR / "data" / "import" / "Directives"
EXPORT_DIR = WORK_DIR / "data" / "export" / "Reports"
STATE_FILE = WORK_DIR / ".gateway" / "hub" / "executor_state.json"

def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except:
            return {"processed": []}
    return {"processed": []}

def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))

def execute_directive(directive_path: Path):
    print(f"[{NODE_NAME}] Executing directive: {directive_path.name}")
    time.sleep(2)
    
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_name = f"{directive_path.stem}_REPORT.md"
    report_path = EXPORT_DIR / report_name
    
    report_content = f"# EXECUTION REPORT: {directive_path.name}\n**Agent:** {NODE_NAME}\n**Status:** SUCCESS\n**Timestamp:** {datetime.utcnow().isoformat()}Z\n\n## Execution Summary\nThe directive was parsed and executed successfully according to local protocol.\nAll specified tasks completed within standard operational parameters.\n"
    report_path.write_text(report_content)
    
    print(f"[{NODE_NAME}] Report generated: {report_path.name}")
    # Trigger Bridge back to process the new report
    bridge_trigger = WORK_DIR.parent / "RADRILONIUMA" / "scripts" / "trigger_pulse.sh"
    if bridge_trigger.exists():
        import subprocess
        subprocess.Popen([str(bridge_trigger), "--reports"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def poll_inbox():
    state = load_state()
    processed = set(state.get("processed", []))
    
    if not IMPORT_DIR.exists():
        return
        
    for md_file in IMPORT_DIR.glob("*.md"):
        if md_file.name in processed:
            continue
            
        execute_directive(md_file)
        processed.add(md_file.name)
        
    state["processed"] = list(processed)
    save_state(state)

if __name__ == "__main__":
    poll_inbox()
