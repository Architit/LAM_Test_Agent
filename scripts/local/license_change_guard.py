#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lam_test_agent_paths import workspace_root
from scripts.local.license_audit_scan import collect_repo, discover_repos


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=False)
    out = (proc.stdout or proc.stderr).strip()
    return proc.returncode, out


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def license_state_for_repo(repo: Path) -> dict[str, Any]:
    row = collect_repo(repo)
    out: dict[str, Any] = {
        "repo_name": row.repo_name,
        "repo_path": row.repo_path,
        "origin_url": row.origin_url,
        "github_slug": row.github_slug,
        "branch": row.branch,
        "license_type": row.license_type,
        "license_file": row.license_file,
        "license_sha256": "",
        "license_last_commit": "",
        "license_last_commit_utc": "",
    }
    if row.license_file:
        p = repo / row.license_file
        if p.exists():
            out["license_sha256"] = sha256_file(p)
        rc, commit = run(["git", "log", "-1", "--format=%H", "--", row.license_file], repo)
        if rc == 0:
            out["license_last_commit"] = commit
        rc, dt = run(["git", "log", "-1", "--format=%cI", "--", row.license_file], repo)
        if rc == 0:
            out["license_last_commit_utc"] = dt
    return out


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def index_by_repo(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(x.get("repo_name", "")): x for x in items if isinstance(x, dict) and x.get("repo_name")}


def approval_allowed(approvals: list[dict[str, Any]], repo_name: str, new_sha: str) -> bool:
    for row in approvals:
        if not isinstance(row, dict):
            continue
        if row.get("repo_name") == repo_name and row.get("license_sha256") == new_sha and row.get("approved") is True:
            return True
    return False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="License change control guard.")
    parser.add_argument("--workspace-root", default=str(workspace_root()))
    parser.add_argument("--max-depth", type=int, default=3)
    parser.add_argument("--mode", choices=["snapshot", "verify"], default="verify")
    parser.add_argument(
        "--baseline-file",
        default="infra/governance/LICENSE_BASELINE.json",
        help="Baseline license state snapshot.",
    )
    parser.add_argument(
        "--approvals-file",
        default="infra/governance/LICENSE_CHANGE_APPROVALS.json",
        help="Explicit approvals for license changes.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = Path(args.workspace_root).expanduser().resolve()
    repo_root = Path(__file__).resolve().parents[2]
    baseline_file = Path(args.baseline_file)
    if not baseline_file.is_absolute():
        baseline_file = repo_root / baseline_file
    approvals_file = Path(args.approvals_file)
    if not approvals_file.is_absolute():
        approvals_file = repo_root / approvals_file

    repos = discover_repos(root, max_depth=max(1, int(args.max_depth)))
    current_rows = [license_state_for_repo(r) for r in repos]
    payload = {
        "generated_at_utc": utc_now(),
        "workspace_root": str(root),
        "repo_count": len(current_rows),
        "repos": current_rows,
    }

    if args.mode == "snapshot":
        baseline_file.parent.mkdir(parents=True, exist_ok=True)
        baseline_file.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        if not approvals_file.exists():
            approvals_file.write_text(json.dumps({"approvals": []}, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "ok", "mode": "snapshot", "baseline_file": str(baseline_file)}, ensure_ascii=True))
        return 0

    baseline = load_json(baseline_file, {})
    approvals = load_json(approvals_file, {"approvals": []})
    if not isinstance(baseline, dict) or not isinstance(baseline.get("repos", []), list):
        print(json.dumps({"status": "error", "error": "baseline_missing_or_invalid", "baseline_file": str(baseline_file)}, ensure_ascii=True))
        return 2
    approval_rows = approvals.get("approvals", []) if isinstance(approvals, dict) else []
    base_by = index_by_repo(baseline.get("repos", []))
    curr_by = index_by_repo(current_rows)

    violations: list[dict[str, Any]] = []
    changed: list[dict[str, Any]] = []

    for repo_name, curr in curr_by.items():
        base = base_by.get(repo_name)
        if not base:
            # New repo enters baseline flow.
            if curr.get("license_sha256"):
                if not approval_allowed(approval_rows, repo_name, str(curr.get("license_sha256", ""))):
                    violations.append(
                        {
                            "repo_name": repo_name,
                            "reason": "new_repo_without_approval",
                            "license_sha256": curr.get("license_sha256", ""),
                        }
                    )
            continue
        if str(base.get("license_sha256", "")) != str(curr.get("license_sha256", "")) or str(base.get("license_type", "")) != str(curr.get("license_type", "")):
            changed.append(
                {
                    "repo_name": repo_name,
                    "baseline_license_type": base.get("license_type", ""),
                    "current_license_type": curr.get("license_type", ""),
                    "baseline_sha256": base.get("license_sha256", ""),
                    "current_sha256": curr.get("license_sha256", ""),
                }
            )
            if not approval_allowed(approval_rows, repo_name, str(curr.get("license_sha256", ""))):
                violations.append(
                    {
                        "repo_name": repo_name,
                        "reason": "license_change_without_approval",
                        "baseline_sha256": base.get("license_sha256", ""),
                        "current_sha256": curr.get("license_sha256", ""),
                    }
                )

    result = {
        "status": "ok" if not violations else "hold",
        "mode": "verify",
        "baseline_file": str(baseline_file),
        "approvals_file": str(approvals_file),
        "changed_count": len(changed),
        "violation_count": len(violations),
        "changed": changed,
        "violations": violations,
    }
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if not violations else 3


if __name__ == "__main__":
    raise SystemExit(main())
