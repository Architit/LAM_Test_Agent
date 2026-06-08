#!/usr/bin/env python3
# Copyright (c) 2026-06-08 RADRILONIUMA / TRIANIUMA Kingdom. All rights reserved.
"""
Sovereign Target Task & Heal Manager (lam_target_task_heal_manager)
Dynamically scans ecosystem organs, queue status, and git state to
regenerate a comprehensive targets, missions, and healing walkthrough list.
"""

import json
import os
import subprocess
from pathlib import Path
from datetime import datetime, timezone

# Root Path
BASE_DIR = Path(__file__).resolve().parents[1]
AMC_GRAPH_FILE = BASE_DIR / ".gateway" / "amc_graph.json"
QUEUE_FILE = BASE_DIR / ".gateway" / "queue.json"
TARGET_TASKS_FILE = BASE_DIR / "lam_target_task_heal_manager" / "TARGET_TASKS.md"

def load_amc_graph():
    if not AMC_GRAPH_FILE.exists():
        return {}
    try:
        with AMC_GRAPH_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[HEAL_MANAGER] Error loading AMC Graph: {e}")
        return {}

def load_queue():
    if not QUEUE_FILE.exists():
        return {"items": []}
    try:
        with QUEUE_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[HEAL_MANAGER] Error loading Queue: {e}")
        return {"items": []}

def get_git_status():
    try:
        res = subprocess.run(["git", "status", "-sb"], cwd=str(BASE_DIR), capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception as e:
        return f"Unknown ({e})"

def scan_organ(meta):
    path_str = meta.get("path")
    if not path_str:
        return {"status": "MISSING_PATH", "identity": False, "patch": False, "bootstrap": False}
    
    path = Path(path_str)
    if not path.exists():
        return {"status": "OFFLINE", "identity": False, "patch": False, "bootstrap": False}
        
    identity_file = path / "IDENTITY.md"
    patch_file = path / "devkit" / "patch.sh"
    bootstrap_file = path / "devkit" / "bootstrap.sh"
    
    return {
        "status": "ONLINE",
        "identity": identity_file.exists(),
        "patch": patch_file.exists(),
        "bootstrap": bootstrap_file.exists(),
        "path": path
    }

def main():
    print("[HEAL_MANAGER] Initiating target task scan...")
    graph = load_amc_graph()
    queue = load_queue()
    git_status = get_git_status()
    
    organs = graph.get("organs", {})
    online_count = 0
    offline_count = 0
    missing_bootstrap = []
    missing_identity = []
    missing_patch = []
    
    organ_rows = []
    for sys_id, meta in sorted(organs.items()):
        scan = scan_organ(meta)
        if scan["status"] == "ONLINE":
            online_count += 1
            if not scan["bootstrap"]:
                missing_bootstrap.append((sys_id, scan["path"]))
            if not scan["identity"]:
                missing_identity.append((sys_id, scan["path"]))
            if not scan["patch"]:
                missing_patch.append((sys_id, scan["path"]))
        else:
            offline_count += 1
            
        status_icon = "🟢 ONLINE" if scan["status"] == "ONLINE" else "🔴 OFFLINE"
        ident_icon = "✅ YES" if scan["identity"] else "❌ NO"
        patch_icon = "✅ YES" if scan["patch"] else "❌ NO"
        boot_icon = "✅ YES" if scan["bootstrap"] else "⚠️ MISSING"
        
        organ_rows.append(
            f"| **{sys_id}** | {meta.get('role', 'UNKNOWN')} | {status_icon} | {ident_icon} | {patch_icon} | {boot_icon} |"
        )
        
    # Analyze Queue for healing opportunities
    queue_items = queue.get("items", [])
    failed_tasks = [item for item in queue_items if item.get("status") == "error"]
    pending_tasks = [item for item in queue_items if item.get("status") == "pending"]
    
    # Generate content
    content = []
    content.append("# ⚜️ SOVEREIGN FOREST: TARGETS & MISSIONS MATRIX ⚜️")
    content.append(f"\n*Generated at (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}*")
    
    content.append("\n> [!NOTE]\n> This matrix is dynamically managed by `lam_target_task_heal_manager` to scan the active state of the Sovereign Forest organs and suggest tasks, campaigns, and healing walkthroughs.")
    
    content.append("\n## I. ACTIVE CAMPAIGN STATUS")
    content.append("- **Current Phase:** `PHASE_11_AUTONOMOUS_INTEGRATION`")
    content.append("- **Current Stage:** `IC_PHASE_11.4_PROJECT_LIFECYCLE` (Cross-organ project orchestration)")
    content.append("- **Resonance Target:** `432 Hz` (Pure)")
    
    content.append("\n## II. SYSTEM HEALING MISSIONS (AUTO-GENERATED)")
    
    healing_needed = False
    
    # 1. Failed Queue Tasks
    if failed_tasks:
        healing_needed = True
        content.append("\n### 🚨 FAILED QUEUE TASKS (HEALING REQUIRED)")
        content.append("The following queue tasks have encountered errors and require remediation:")
        for task in failed_tasks:
            content.append(f"- **Task ID:** `{task['id']}`")
            content.append(f"  - **Owner Organ:** `{task['payload'].get('owner')}`")
            content.append(f"  - **Intent:** `{task['payload'].get('intent')}`")
            content.append(f"  - **Error Msg:** `{task.get('error_msg')}`")
            content.append("  - **Recommended Action:** Check the organ's error logs, verify task payload arguments (e.g. hash or file parameters), resolve the issue, and rerun/re-enqueue the task.")
            
    # 2. Missing DevKit bootstraps/patches
    if missing_bootstrap or missing_patch:
        healing_needed = True
        content.append("\n### ⚠️ DEV_KIT HEALING MISSIONS")
        content.append("The following organs are missing essential DevKit scripts:")
        for sys_id, path in missing_bootstrap:
            content.append(f"- [ ] **{sys_id}**: Missing `devkit/bootstrap.sh` in [{sys_id} workspace](file://{path})")
        for sys_id, path in missing_patch:
            content.append(f"- [ ] **{sys_id}**: Missing `devkit/patch.sh` in [{sys_id} workspace](file://{path})")
            
    # 3. Missing Identity documents
    if missing_identity:
        healing_needed = True
        content.append("\n### ⚠️ IDENTITY HEALING MISSIONS")
        content.append("The following organs do not have an `IDENTITY.md` file:")
        for sys_id, path in missing_identity:
            content.append(f"- [ ] **{sys_id}**: Create `IDENTITY.md` in [{sys_id} workspace](file://{path})")
            
    if not healing_needed:
        content.append("\n> [!TIP]\n> 🟢 **No healing actions required.** All active organs are online and their local DevKit configurations are complete.")

    content.append("\n## III. CURRENT CAMPAIGN WALKTHROUGH & SUGGESTED TASKS")
    content.append("Here is the list of suggested tasks to advance the current campaign:")
    content.append("- [ ] **Task 1: Verify Telemetry Heartbeat**")
    content.append("  - Check `/home/architit/LAM_CORE/RADRILONIUMA/.gateway/telemetry_events.jsonl` to ensure the system is emitting pulses.")
    content.append("- [ ] **Task 2: Clear Failed Queue Tasks**")
    content.append("  - Run diagnostics on any failed queue items and clear or re-enqueue them.")
    content.append("- [ ] **Task 3: Perform Dry-Run Rollout**")
    content.append("  - Run `bash devkit/ecosystem_rollout.sh --dry-run` to verify dry-run patch propagation.")
    content.append("- [ ] **Task 4: Run Governance Test Suite**")
    content.append("  - Run `bash scripts/test_entrypoint.sh --governance` to verify 100% compliance.")

    content.append("\n## III.B SOVEREIGN FOREST: 24 TARGET ORGAN TASKS (MINIMAL COMPLIANCE)")
    content.append("These 24 tasks are dynamically generated to ensure active vital status (heartbeat/breath) across the 24 primary MCP server and organ nodes:")
    content.append("- [ ] **Task 01 (AYAS-01 / Identity):** Verify SSH/GCR credentials mapping and run preflight check.")
    content.append("- [ ] **Task 02 (LRPT-01 / Tools):** Audit local devkit version and environment baseline.")
    content.append("- [ ] **Task 03 (VLRM-01 / Vision):** Generate updated ecosystem topology map.")
    content.append("- [ ] **Task 04 (CRTD-01 / Heart):** Run core health and verify system state sync.")
    content.append("- [ ] **Task 05 (TSPT-01 / Tasks):** Clean up old task specification cache.")
    content.append("- [ ] **Task 06 (FMLN-01 / Mode):** Verify system transition state constraints.")
    content.append("- [ ] **Task 07 (GLKT-01 / Log):** Verify logger formatting and telemetry stream.")
    content.append("- [ ] **Task 08 (JNSR-01 / Journal):** Record the current Phase 11.4 session log entry.")
    content.append("- [ ] **Task 09 (KTRD-01 / Kits):** Run tool preflight baseline sweeps.")
    content.append("- [ ] **Task 10 (LVNS-01 / Flow):** Verify task queue lease TTL and timeouts.")
    content.append("- [ ] **Task 11 (MLVD-01 / Module):** Audit package imports for cognitive scripts.")
    content.append("- [ ] **Task 12 (XNVR-01 / Atlas):** Verify AMC graph consistency and links.")
    content.append("- [ ] **Task 13 (PLTS-01 / Protocol):** Verify compliance with interaction protocol.")
    content.append("- [ ] **Task 14 (SRZJ-01 / Contract):** Verify zero-trust check constraints on ingress.")
    content.append("- [ ] **Task 15 (VRBN-01 / Chronolog):** Audit timestamp-utc formatting across files.")
    content.append("- [ ] **Task 16 (VRLS-01 / Topology):** Verify active target lists in rollout tools.")
    content.append("- [ ] **Task 17 (ZRDG-01 / Matrix):** Verify matrix routing assignments.")
    content.append("- [ ] **Task 18 (RBTK-01 / Genesis):** Run genesis validation test suite.")
    content.append("- [ ] **Task 19 (CDKS-01 / Cognition):** Run Codex self-refinement checks.")
    content.append("- [ ] **Task 20 (RDTR-01 / Routing):** Audit LLM routing provider endpoints.")
    content.append("- [ ] **Task 21 (LAM-01 / Mind):** Verify primary mind core is online.")
    content.append("- [ ] **Task 22 (ARKS-01 / Ark):** Secure database backup integrity.")
    content.append("- [ ] **Task 23 (TRNM-01 / Kingdom):** Audit kingdom constitution compliance.")
    content.append("- [ ] **Task 24 (ALGS-01 / Logs):** Run global log de-duplication sweep.")

    content.append("\n## IV. SOVEREIGN FOREST ORGAN STATES")
    content.append(f"Currently tracking **{len(organs)}** organs (**{online_count}** Online, **{offline_count}** Offline/External):")
    content.append("\n| Organ System ID | Role | Status | Identity.md | devkit/patch.sh | devkit/bootstrap.sh |")
    content.append("| :--- | :--- | :--- | :---: | :---: | :---: |")
    for row in organ_rows:
        content.append(row)
        
    content.append("\n## V. GIT STATE & WORKSPACE COMPLIANCE")
    content.append(f"```bash\n{git_status}\n```")
    
    # Save the file
    TARGET_TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with TARGET_TASKS_FILE.open("w", encoding="utf-8") as f:
        f.write("\n".join(content) + "\n")
        
    print(f"[HEAL_MANAGER] Targets and missions matrix successfully regenerated at: {TARGET_TASKS_FILE}")

if __name__ == "__main__":
    main()
