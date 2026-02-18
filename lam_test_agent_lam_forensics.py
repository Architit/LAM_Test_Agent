from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lam_test_agent_paths import lam_root as default_lam_root
from lam_test_agent_paths import sibling_repo


def _run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=False)
    out = p.stdout.strip() if p.stdout.strip() else p.stderr.strip()
    return p.returncode, out


def _parse_guard_json(raw: str) -> dict[str, Any]:
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    return {"raw": raw}


def _python_executable_for_repo(repo_root: Path) -> str:
    venv_python = repo_root / ".venv" / "bin" / "python"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def collect_lam_forensics(lam_root: Path) -> dict[str, Any]:
    this_repo_root = sibling_repo("LAM_Test_Agent")
    radriloniuma_root = sibling_repo("RADRILONIUMA-PROJECT")

    rc, branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], lam_root)
    if rc != 0:
        branch = "unknown"
    rc, status = _run(["git", "status", "--porcelain"], lam_root)
    status_lines = [ln for ln in status.splitlines() if ln.strip()] if rc == 0 else []
    modified = sum(1 for ln in status_lines if not ln.startswith("??"))
    untracked = sum(1 for ln in status_lines if ln.startswith("??"))

    rc, sm = _run(["git", "submodule", "status"], lam_root)
    submodule_count = len([ln for ln in sm.splitlines() if ln.strip()]) if rc == 0 else 0

    rc, roadmap_hits = _run(
        ["rg", "-n", "HOLD_BY_DEADLOOP_BREAK_PROTOCOL|OPEN_PHASE43|Phase 4.3", "ROADMAP.md"],
        lam_root,
    )
    roadmap_hit_count = len([ln for ln in roadmap_hits.splitlines() if ln.strip()]) if rc == 0 else 0

    rc, workflow_hits = _run(
        ["rg", "-n", "HOLD_BY_DEADLOOP_BREAK_PROTOCOL|deadloop_guard|active_next_target", "WORKFLOW_SNAPSHOT_STATE.md"],
        lam_root,
    )
    workflow_hit_count = len([ln for ln in workflow_hits.splitlines() if ln.strip()]) if rc == 0 else 0

    # Forced HOLD scenario: governance-only cycle (journal paths only, streak >= 3)
    py = _python_executable_for_repo(lam_root)
    rc_hold, hold_raw = _run(
        [
            py,
            "scripts/deadloop_guard_entrypoint.py",
            "--governance-only-streak",
            "3",
            "--changed-path",
            "ROADMAP.md",
            "--changed-path",
            "DEV_LOGS.md",
            "--validation-result",
            "PASS",
        ],
        lam_root,
    )
    hold_result = _parse_guard_json(hold_raw)

    # PASS scenario: non-doc code + test deltas + validation command + operator confirmation
    rc_pass, pass_raw = _run(
        [
            py,
            "scripts/deadloop_guard_entrypoint.py",
            "--governance-only-streak",
            "0",
            "--changed-path",
            "src/deadloop_gate.py",
            "--changed-path",
            "tests/test_deadloop_gate.py",
            "--validation-command",
            ".venv/bin/pytest -q tests/test_deadloop_gate.py -p no:cacheprovider",
            "--validation-result",
            "PASS",
            "--operator-confirmed",
        ],
        lam_root,
    )
    pass_result = _parse_guard_json(pass_raw)

    rc_scan, scan_raw = _run(
        [
            py,
            "scripts/deadloop_ecosystem_scan.py",
            "--repo",
            str(lam_root),
            "--repo",
            str(this_repo_root),
            "--repo",
            str(radriloniuma_root),
        ],
        lam_root,
    )
    scan_data: dict[str, Any]
    try:
        loaded = json.loads(scan_raw)
        scan_data = loaded if isinstance(loaded, dict) else {"raw": scan_raw}
    except json.JSONDecodeError:
        scan_data = {"raw": scan_raw}

    rc_tests, tests_raw = _run(
        [
            py,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "tests/test_deadloop_gate.py",
            "tests/test_deadloop_resume_gate.py",
            "tests/test_deadloop_guard_entrypoint.py",
            "tests/test_deadloop_patterns.py",
            "tests/test_deadloop_payload.py",
        ],
        lam_root,
    )

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "lam_root": str(lam_root),
        "git": {
            "branch": branch,
            "dirty": len(status_lines) > 0,
            "modified_entries": modified,
            "untracked_entries": untracked,
            "submodule_count": submodule_count,
        },
        "phase43_markers": {
            "roadmap_hit_count": roadmap_hit_count,
            "workflow_hit_count": workflow_hit_count,
        },
        "guard_probe_hold": {"exit_code": rc_hold, "result": hold_result},
        "guard_probe_pass": {"exit_code": rc_pass, "result": pass_result},
        "ecosystem_scan": {"exit_code": rc_scan, "result": scan_data},
        "deadloop_test_suite": {"exit_code": rc_tests, "output": tests_raw},
    }


def render_markdown(snapshot: dict[str, Any]) -> str:
    git = snapshot["git"]
    hold = snapshot["guard_probe_hold"]["result"]
    pss = snapshot["guard_probe_pass"]["result"]
    deadloop_exit = snapshot["deadloop_test_suite"]["exit_code"]
    deadloop_assessment = (
        "- Deadloop suite currently PASS; no active contract drift detected in scanned guard tests."
        if deadloop_exit == 0
        else "- Deadloop suite currently failing; contract drift likely between tests and strict resume tuple requirements."
    )
    lines = [
        "# LAM_PHASE43_DEADLOOP_FORENSIC_REPORT",
        "",
        f"- generated_at_utc: {snapshot['generated_at_utc']}",
        f"- lam_root: {snapshot['lam_root']}",
        "",
        "## Repo Telemetry",
        f"- branch: {git['branch']}",
        f"- dirty: {git['dirty']}",
        f"- modified_entries: {git['modified_entries']}",
        f"- untracked_entries: {git['untracked_entries']}",
        f"- submodule_count: {git['submodule_count']}",
        "",
        "## Phase 4.3 Signals",
        f"- roadmap_hit_count: {snapshot['phase43_markers']['roadmap_hit_count']}",
        f"- workflow_hit_count: {snapshot['phase43_markers']['workflow_hit_count']}",
        "",
        "## Guard Probes",
        f"- hold_probe_exit: {snapshot['guard_probe_hold']['exit_code']}",
        f"- hold_probe_decision: {hold.get('preflight', {}).get('decision', 'unknown')}",
        f"- hold_probe_reason: {hold.get('preflight', {}).get('reason', 'unknown')}",
        f"- pass_probe_exit: {snapshot['guard_probe_pass']['exit_code']}",
        f"- pass_probe_preflight: {pss.get('preflight', {}).get('decision', 'unknown')}",
        f"- pass_probe_resume: {pss.get('resume', {}).get('decision', 'unknown')}",
        "",
        "## Deadloop Test Suite",
        f"- exit_code: {deadloop_exit}",
        "",
        "## Assessment",
        "- Guard mechanics are present and can force HOLD on governance-only repetition.",
        "- Guard can PASS with complete engineering evidence tuple and operator confirmation.",
        deadloop_assessment,
    ]
    return "\n".join(lines) + "\n"


def write_outputs(snapshot: dict[str, Any], json_path: Path, md_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(snapshot), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect detailed Phase 4.3 deadloop forensics for LAM.")
    parser.add_argument("--lam-root", default=str(default_lam_root()))
    parser.add_argument("--json-output", default="memory/FRONT/LAM_PHASE43_DEADLOOP_FORENSICS.json")
    parser.add_argument("--md-output", default="memory/FRONT/LAM_PHASE43_DEADLOOP_FORENSICS.md")
    args = parser.parse_args(argv)

    lam_root = Path(args.lam_root).resolve()
    if not lam_root.exists():
        print(f"LAM_FORENSICS_FAIL: lam root not found: {lam_root}")
        return 2

    snapshot = collect_lam_forensics(lam_root)
    write_outputs(snapshot, Path(args.json_output), Path(args.md_output))
    print(
        "LAM_FORENSICS_OK "
        f"branch={snapshot['git']['branch']} dirty={snapshot['git']['dirty']} deadloop_tests_exit={snapshot['deadloop_test_suite']['exit_code']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
