from __future__ import annotations

import argparse
import json
import re
import socket
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lam_test_agent_paths import workspace_root

_LOCAL_REPO_ROOT = Path(__file__).resolve().parent
_SEMANTIC_IDENTITY_DIRS = (
    "memory/FRONT",
    "memory/AVANGARD",
    "memory/ARCHIVE",
    "memory/GUARD_HEAL",
)


@dataclass(frozen=True)
class RepoTelemetry:
    repo_name: str
    repo_path: str
    branch: str
    dirty: bool
    modified_entries: int
    untracked_entries: int
    ahead: int | None
    behind: int | None
    last_commit: str
    last_commit_utc: str
    remotes: list[str]
    submodule_count: int
    has_tests_dir: bool
    has_pytest_ini: bool
    has_dev_requirements: bool
    has_ci_workflows: bool
    has_roadmap: bool
    has_dev_logs: bool
    has_interaction_protocol: bool


def _run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=False)
    out = (p.stdout or p.stderr).strip()
    return p.returncode, out


def discover_repos(root: Path, max_depth: int = 2) -> list[Path]:
    repos: list[Path] = []
    root = root.resolve()
    if (root / ".git").exists():
        repos.append(root)
    for git_dir in root.glob("*/.git"):
        if git_dir.exists():
            repos.append(git_dir.parent)
    if max_depth >= 2:
        for git_dir in root.glob("*/*/.git"):
            if git_dir.exists():
                repos.append(git_dir.parent)
    dedup = sorted({p.resolve() for p in repos})
    return [Path(p) for p in dedup]


def collect_repo(repo: Path) -> RepoTelemetry:
    rc, branch_out = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo)
    branch = branch_out if rc == 0 else "unknown"

    rc, status_out = _run(["git", "status", "--porcelain"], repo)
    lines = [ln for ln in status_out.splitlines() if ln.strip()] if rc == 0 else []
    dirty = len(lines) > 0
    untracked = sum(1 for ln in lines if ln.startswith("??"))
    modified = len(lines) - untracked

    ahead: int | None = None
    behind: int | None = None
    rc, ab_out = _run(["git", "rev-list", "--left-right", "--count", "@{upstream}...HEAD"], repo)
    if rc == 0:
        parts = ab_out.split()
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            behind = int(parts[0])
            ahead = int(parts[1])

    rc, commit_hash = _run(["git", "log", "-1", "--format=%H"], repo)
    last_commit = commit_hash if rc == 0 else "unknown"
    rc, commit_date = _run(["git", "log", "-1", "--format=%cI"], repo)
    last_commit_utc = commit_date if rc == 0 else "unknown"

    rc, remotes_out = _run(["git", "remote"], repo)
    remotes = sorted([r.strip() for r in remotes_out.splitlines() if r.strip()]) if rc == 0 else []

    rc, sm_out = _run(["git", "submodule", "status"], repo)
    submodule_count = len([ln for ln in sm_out.splitlines() if ln.strip()]) if rc == 0 else 0

    return RepoTelemetry(
        repo_name=repo.name,
        repo_path=str(repo),
        branch=branch,
        dirty=dirty,
        modified_entries=modified,
        untracked_entries=untracked,
        ahead=ahead,
        behind=behind,
        last_commit=last_commit,
        last_commit_utc=last_commit_utc,
        remotes=remotes,
        submodule_count=submodule_count,
        has_tests_dir=(repo / "tests").exists(),
        has_pytest_ini=(repo / "pytest.ini").exists(),
        has_dev_requirements=(repo / "requirements-dev.txt").exists(),
        has_ci_workflows=(repo / ".github" / "workflows").exists(),
        has_roadmap=(repo / "ROADMAP.md").exists(),
        has_dev_logs=(repo / "DEV_LOGS.md").exists(),
        has_interaction_protocol=(repo / "INTERACTION_PROTOCOL.md").exists(),
    )


def evaluate_archivator_handoff(rows: list[RepoTelemetry]) -> dict[str, Any]:
    archivator = next((r for r in rows if r.repo_name == "Archivator_Agent"), None)
    if archivator is None:
        return {
            "scope_active": False,
            "handoff_ok": True,
            "mirrored_repo_count": 0,
            "eligible_repo_count": 0,
            "missing_mirrors": [],
            "stale_mirrors": [],
        }

    archivator_root = Path(archivator.repo_path)
    subtree_repos_root = archivator_root / "SubtreeHub" / "repos"
    if not subtree_repos_root.exists():
        return {
            "scope_active": True,
            "handoff_ok": False,
            "mirrored_repo_count": 0,
            "eligible_repo_count": 0,
            "missing_mirrors": ["SubtreeHub/repos"],
            "stale_mirrors": [],
        }

    eligible = [
        r
        for r in rows
        if r.repo_name != "Archivator_Agent" and not Path(r.repo_path).resolve().is_relative_to(archivator_root.resolve())
    ]
    missing: list[str] = []
    stale: list[str] = []
    mirrored = 0
    for repo in eligible:
        source_snapshot = Path(repo.repo_path) / "WORKFLOW_SNAPSHOT_STATE.md"
        if not source_snapshot.exists():
            continue
        mirror_snapshot = subtree_repos_root / repo.repo_name / "WORKFLOW_SNAPSHOT_STATE.md"
        if not mirror_snapshot.exists():
            missing.append(repo.repo_name)
            continue
        mirrored += 1
        try:
            if mirror_snapshot.stat().st_mtime + 1 < source_snapshot.stat().st_mtime:
                stale.append(repo.repo_name)
        except OSError:
            stale.append(repo.repo_name)

    return {
        "scope_active": True,
        "handoff_ok": len(missing) == 0 and len(stale) == 0,
        "mirrored_repo_count": mirrored,
        "eligible_repo_count": len(eligible),
        "missing_mirrors": missing,
        "stale_mirrors": stale,
    }


def _normalize_semantic_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _discover_latest_semantic_identity_files(base: Path) -> list[Path]:
    found: list[Path] = []
    for rel_dir in _SEMANTIC_IDENTITY_DIRS:
        directory = (base / rel_dir).resolve()
        if not directory.exists() or not directory.is_dir():
            continue
        candidates = [p for p in directory.glob("SEMANTIC_IDENTITY_MAP*.tsv") if p.is_file()]
        if not candidates:
            continue
        try:
            latest = max(candidates, key=lambda p: (p.stat().st_mtime, p.name))
        except OSError:
            latest = sorted(candidates)[-1]
        found.append(latest)
    return found


def evaluate_semantic_identity_health(root: Path) -> dict[str, Any]:
    files: list[Path] = []
    seen: set[Path] = set()
    for base in (root.resolve(), _LOCAL_REPO_ROOT):
        for candidate in _discover_latest_semantic_identity_files(base):
            if candidate.exists() and candidate not in seen:
                seen.add(candidate)
                files.append(candidate)
    if not files:
        return {
            "scope_active": False,
            "identity_ok": True,
            "checked_files": [],
            "checked_rows": 0,
            "unresolved_count": 0,
            "provisional_count": 0,
            "templated_true_name_count": 0,
            "violations": [],
        }

    unresolved_count = 0
    provisional_count = 0
    templated_true_name_count = 0
    checked_rows = 0
    violations: list[dict[str, str]] = []

    for path in files:
        lines = path.read_text(encoding="utf-8").splitlines()
        for line_no, raw in enumerate(lines[1:], start=2):
            if not raw.strip():
                continue
            cols = raw.split("\t")
            if len(cols) < 8:
                continue
            checked_rows += 1
            repo = cols[0]
            true_name = cols[2]
            call_sign = cols[3]
            status = cols[6]
            source = cols[7]

            if true_name == "UNRESOLVED_TRUE_NAME" or status == "HOLD" or source == "PENDING_GOVERNANCE_MAPPING":
                unresolved_count += 1
                violations.append(
                    {
                        "file": str(path),
                        "line": str(line_no),
                        "repo": repo,
                        "type": "unresolved_identity",
                        "details": f"true_name={true_name}, status={status}, source={source}",
                    }
                )

            if status == "ACTIVE_PROVISIONAL" or source == "GOVERNANCE_PROVISIONAL_RULE_V1":
                provisional_count += 1
                violations.append(
                    {
                        "file": str(path),
                        "line": str(line_no),
                        "repo": repo,
                        "type": "provisional_identity",
                        "details": f"status={status}, source={source}",
                    }
                )

            if _normalize_semantic_token(true_name) == f"{_normalize_semantic_token(call_sign)}shpoisat":
                templated_true_name_count += 1
                violations.append(
                    {
                        "file": str(path),
                        "line": str(line_no),
                        "repo": repo,
                        "type": "templated_true_name",
                        "details": f"true_name={true_name}, call_sign={call_sign}",
                    }
                )

    return {
        "scope_active": True,
        "identity_ok": len(violations) == 0,
        "checked_files": [str(p) for p in files],
        "checked_rows": checked_rows,
        "unresolved_count": unresolved_count,
        "provisional_count": provisional_count,
        "templated_true_name_count": templated_true_name_count,
        "violations": violations[:50],
    }


def collect_ecosystem(root: Path) -> dict[str, Any]:
    repos = discover_repos(root)
    rows = [collect_repo(r) for r in repos]
    archivator_handoff = evaluate_archivator_handoff(rows)
    semantic_identity = evaluate_semantic_identity_health(root)
    github_dns_resolvable = True
    try:
        socket.getaddrinfo("github.com", 443)
    except OSError:
        github_dns_resolvable = False
    local_dependency_mirror_ready = (
        (root / "LAM-Codex_Agent" / ".git").exists()
        and (
            (root / "LAM_Comunication_Agent" / ".git").exists()
            or (root / "LAM_Communication_Agent" / ".git").exists()
        )
    )

    summary = {
        "repo_count": len(rows),
        "dirty_repos": sum(1 for r in rows if r.dirty),
        "repos_with_tests": sum(1 for r in rows if r.has_tests_dir),
        "repos_with_ci": sum(1 for r in rows if r.has_ci_workflows),
        "repos_with_governance_triad": sum(
            1 for r in rows if r.has_roadmap and r.has_dev_logs and r.has_interaction_protocol
        ),
        "repos_with_submodules": sum(1 for r in rows if r.submodule_count > 0),
        "github_dns_resolvable": github_dns_resolvable,
        "local_dependency_mirror_ready": local_dependency_mirror_ready,
        "archivator_scope_active": archivator_handoff["scope_active"],
        "archivator_handoff_ok": archivator_handoff["handoff_ok"],
        "archivator_mirrored_repo_count": archivator_handoff["mirrored_repo_count"],
        "archivator_eligible_repo_count": archivator_handoff["eligible_repo_count"],
        "archivator_missing_mirrors_count": len(archivator_handoff["missing_mirrors"]),
        "archivator_stale_mirrors_count": len(archivator_handoff["stale_mirrors"]),
        "semantic_identity_scope_active": semantic_identity["scope_active"],
        "semantic_identity_ok": semantic_identity["identity_ok"],
        "semantic_identity_unresolved_count": semantic_identity["unresolved_count"],
        "semantic_identity_provisional_count": semantic_identity["provisional_count"],
        "semantic_identity_templated_true_name_count": semantic_identity["templated_true_name_count"],
    }
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "root": str(root.resolve()),
        "summary": summary,
        "archivator_handoff": archivator_handoff,
        "semantic_identity": semantic_identity,
        "repos": [asdict(r) for r in rows],
    }


def render_markdown(snapshot: dict[str, Any]) -> str:
    s = snapshot["summary"]
    lines = [
        "# ECOSYSTEM_TELEMETRY_SNAPSHOT",
        "",
        f"- generated_at_utc: {snapshot['generated_at_utc']}",
        f"- root: {snapshot['root']}",
        "",
        "## Summary",
        f"- repo_count: {s['repo_count']}",
        f"- dirty_repos: {s['dirty_repos']}",
        f"- repos_with_tests: {s['repos_with_tests']}",
        f"- repos_with_ci: {s['repos_with_ci']}",
        f"- repos_with_governance_triad: {s['repos_with_governance_triad']}",
        f"- repos_with_submodules: {s['repos_with_submodules']}",
        f"- github_dns_resolvable: {s.get('github_dns_resolvable', 'unknown')}",
        f"- local_dependency_mirror_ready: {s.get('local_dependency_mirror_ready', 'unknown')}",
        f"- archivator_scope_active: {s.get('archivator_scope_active', 'unknown')}",
        f"- archivator_handoff_ok: {s.get('archivator_handoff_ok', 'unknown')}",
        f"- archivator_mirrored_repo_count: {s.get('archivator_mirrored_repo_count', 0)}",
        f"- archivator_eligible_repo_count: {s.get('archivator_eligible_repo_count', 0)}",
        f"- archivator_missing_mirrors_count: {s.get('archivator_missing_mirrors_count', 0)}",
        f"- archivator_stale_mirrors_count: {s.get('archivator_stale_mirrors_count', 0)}",
        f"- semantic_identity_scope_active: {s.get('semantic_identity_scope_active', 'unknown')}",
        f"- semantic_identity_ok: {s.get('semantic_identity_ok', 'unknown')}",
        f"- semantic_identity_unresolved_count: {s.get('semantic_identity_unresolved_count', 0)}",
        f"- semantic_identity_provisional_count: {s.get('semantic_identity_provisional_count', 0)}",
        f"- semantic_identity_templated_true_name_count: {s.get('semantic_identity_templated_true_name_count', 0)}",
        "",
        "## Repo Table",
        "| Repo | Branch | Dirty | Ahead | Behind | Tests | CI | Governance Triad | Submodules |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in snapshot["repos"]:
        governance = r["has_roadmap"] and r["has_dev_logs"] and r["has_interaction_protocol"]
        ahead = "" if r["ahead"] is None else str(r["ahead"])
        behind = "" if r["behind"] is None else str(r["behind"])
        lines.append(
            f"| {r['repo_name']} | {r['branch']} | {int(r['dirty'])} | {ahead} | {behind} | "
            f"{int(r['has_tests_dir'])} | {int(r['has_ci_workflows'])} | {int(governance)} | {r['submodule_count']} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_files(snapshot: dict[str, Any], json_path: Path, md_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(snapshot), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect telemetry from ecosystem repositories.")
    parser.add_argument("--root", default=str(workspace_root()), help="Ecosystem root directory.")
    parser.add_argument(
        "--json-output",
        default="memory/FRONT/ECOSYSTEM_TELEMETRY_SNAPSHOT.json",
        help="JSON output path (relative to current repo).",
    )
    parser.add_argument(
        "--md-output",
        default="memory/FRONT/ECOSYSTEM_TELEMETRY_SNAPSHOT.md",
        help="Markdown output path (relative to current repo).",
    )
    args = parser.parse_args(argv)

    root = Path(args.root)
    if not root.exists():
        print(f"ECOSYSTEM_TELEMETRY_FAIL: root not found: {root}")
        return 2

    snapshot = collect_ecosystem(root)
    write_files(snapshot, Path(args.json_output), Path(args.md_output))
    print(
        "ECOSYSTEM_TELEMETRY_OK "
        f"repos={snapshot['summary']['repo_count']} dirty={snapshot['summary']['dirty_repos']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
