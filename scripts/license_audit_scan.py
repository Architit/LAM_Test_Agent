#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lam_test_agent_paths import workspace_root


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=False)
    out = (proc.stdout or proc.stderr).strip()
    return proc.returncode, out


def discover_repos(root: Path, max_depth: int = 3) -> list[Path]:
    root = root.resolve()
    out: list[Path] = []
    if (root / ".git").exists():
        out.append(root)
    pattern = "/".join(["*"] * max(1, max_depth)) + "/.git"
    for p in root.glob(pattern):
        if p.exists():
            out.append(p.parent.resolve())
    # Also include shallower levels.
    for depth in range(1, max_depth):
        pat = "/".join(["*"] * depth) + "/.git"
        for p in root.glob(pat):
            if p.exists():
                out.append(p.parent.resolve())
    return sorted(set(out))


def parse_github_slug(url: str) -> str:
    clean = url.strip()
    clean = re.sub(r"\.git$", "", clean)
    m = re.search(r"github\.com[:/]+([^/]+/[^/]+)$", clean)
    return m.group(1) if m else ""


def detect_license_type(text: str) -> str:
    t = text.lower()
    if "mit license" in t:
        return "MIT"
    if "apache license" in t and "version 2.0" in t:
        return "Apache-2.0"
    if "gnu affero general public license" in t and "version 3" in t:
        return "AGPL-3.0"
    if "gnu general public license" in t and "version 3" in t:
        return "GPL-3.0"
    if "gnu general public license" in t and "version 2" in t:
        return "GPL-2.0"
    if "mozilla public license" in t and "2.0" in t:
        return "MPL-2.0"
    if "redistribution and use in source and binary forms" in t and "neither the name" in t:
        return "BSD-3-Clause"
    if "redistribution and use in source and binary forms" in t:
        return "BSD-2-Clause"
    if "the unlicense" in t:
        return "Unlicense"
    if "all rights reserved" in t and "permission" not in t:
        return "Proprietary"
    return "UNKNOWN"


def find_license_file(repo: Path) -> Path | None:
    candidates = [
        "LICENSE",
        "LICENSE.md",
        "LICENSE.txt",
        "COPYING",
        "COPYING.md",
        "COPYING.txt",
    ]
    for name in candidates:
        p = repo / name
        if p.exists() and p.is_file():
            return p
    # case-insensitive fallback
    for p in repo.iterdir():
        if not p.is_file():
            continue
        u = p.name.upper()
        if u.startswith("LICENSE") or u.startswith("COPYING"):
            return p
    return None


def extract_spdx_hint(repo: Path) -> str:
    package_json = repo / "package.json"
    if package_json.exists():
        try:
            payload = json.loads(package_json.read_text(encoding="utf-8"))
            lic = payload.get("license")
            if isinstance(lic, str) and lic.strip():
                return lic.strip()
        except json.JSONDecodeError:
            pass

    for file_name in ("pyproject.toml", "Cargo.toml"):
        p = repo / file_name
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        m = re.search(r'^\s*license\s*=\s*["\']([^"\']+)["\']', text, flags=re.MULTILINE)
        if m:
            return m.group(1).strip()
    return ""


@dataclass(frozen=True)
class LicenseRepoRow:
    repo_name: str
    repo_path: str
    origin_url: str
    github_slug: str
    github_default_branch: str
    branch: str
    license_file: str
    license_type: str
    spdx_hint: str
    status: str
    remediation: str


def collect_repo(repo: Path) -> LicenseRepoRow:
    rc, origin = run(["git", "config", "--get", "remote.origin.url"], repo)
    origin_url = origin if rc == 0 else ""
    github_slug = parse_github_slug(origin_url)

    rc, branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo)
    branch_name = branch if rc == 0 else "unknown"

    rc, head_ref = run(["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"], repo)
    if rc == 0 and "/" in head_ref:
        default_branch = head_ref.split("/", 1)[1]
    else:
        default_branch = branch_name

    license_file = find_license_file(repo)
    license_path = str(license_file.relative_to(repo)) if license_file else ""
    license_type = "MISSING"
    if license_file:
        text = license_file.read_text(encoding="utf-8", errors="replace")
        license_type = detect_license_type(text)
    spdx_hint = extract_spdx_hint(repo)

    status = "ok"
    remediation = "none"
    if not github_slug:
        status = "warn_non_github_remote"
        remediation = "verify repository host policy and ensure explicit LICENSE"
    if not license_file:
        status = "missing_license"
        remediation = "add LICENSE file and commit to default branch"
    elif license_type == "UNKNOWN" and not spdx_hint:
        status = "unknown_license_type"
        remediation = "add SPDX identifier in manifest and verify LICENSE text"

    return LicenseRepoRow(
        repo_name=repo.name,
        repo_path=str(repo),
        origin_url=origin_url,
        github_slug=github_slug,
        github_default_branch=default_branch,
        branch=branch_name,
        license_file=license_path,
        license_type=license_type,
        spdx_hint=spdx_hint,
        status=status,
        remediation=remediation,
    )


def build_report(rows: list[LicenseRepoRow], root: Path) -> dict[str, Any]:
    status_counts = Counter(r.status for r in rows)
    license_counts = Counter(r.license_type for r in rows)
    missing = [asdict(r) for r in rows if r.status == "missing_license"]
    unknown = [asdict(r) for r in rows if r.status == "unknown_license_type"]
    non_github = [asdict(r) for r in rows if r.status == "warn_non_github_remote"]
    return {
        "generated_at_utc": utc_now(),
        "workspace_root": str(root),
        "summary": {
            "repo_count": len(rows),
            "status_counts": dict(status_counts),
            "license_type_counts": dict(license_counts),
            "missing_license_count": len(missing),
            "unknown_license_type_count": len(unknown),
            "non_github_remote_count": len(non_github),
        },
        "missing_license_repos": missing,
        "unknown_license_repos": unknown,
        "non_github_remote_repos": non_github,
        "repos": [asdict(r) for r in rows],
    }


def to_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# LICENSE AUDIT REPORT")
    lines.append("")
    lines.append(f"- generated_at_utc: `{report.get('generated_at_utc', '')}`")
    lines.append(f"- workspace_root: `{report.get('workspace_root', '')}`")
    summary = report.get("summary", {})
    lines.append(f"- repo_count: `{summary.get('repo_count', 0)}`")
    lines.append(f"- missing_license_count: `{summary.get('missing_license_count', 0)}`")
    lines.append(f"- unknown_license_type_count: `{summary.get('unknown_license_type_count', 0)}`")
    lines.append(f"- non_github_remote_count: `{summary.get('non_github_remote_count', 0)}`")
    lines.append("")
    lines.append("## Status Counts")
    for k, v in sorted((summary.get("status_counts") or {}).items()):
        lines.append(f"- `{k}`: {v}")
    lines.append("")
    lines.append("## License Type Counts")
    for k, v in sorted((summary.get("license_type_counts") or {}).items()):
        lines.append(f"- `{k}`: {v}")
    lines.append("")
    lines.append("## Repository Matrix")
    lines.append("")
    lines.append("| repo | status | license | license_file | github | default_branch | remediation |")
    lines.append("|---|---|---|---|---|---|---|")
    for row in report.get("repos", []):
        lines.append(
            "| {repo} | {status} | {lic} | {lf} | {gh} | {db} | {rem} |".format(
                repo=row.get("repo_name", ""),
                status=row.get("status", ""),
                lic=row.get("license_type", ""),
                lf=row.get("license_file", ""),
                gh=row.get("github_slug", "") or "-",
                db=row.get("github_default_branch", "") or "-",
                rem=row.get("remediation", ""),
            )
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan workspace repositories and audit license coverage.")
    parser.add_argument("--workspace-root", default=str(workspace_root()))
    parser.add_argument("--max-depth", type=int, default=3)
    parser.add_argument("--json-out", default="")
    parser.add_argument("--md-out", default="")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = Path(args.workspace_root).expanduser().resolve()
    rows = [collect_repo(repo) for repo in discover_repos(root, max_depth=max(1, int(args.max_depth)))]
    report = build_report(rows, root=root)
    date_tag = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    json_out = Path(args.json_out) if args.json_out else (Path(__file__).resolve().parents[1] / "infra" / "governance" / f"LICENSE_AUDIT_REPORT_{date_tag}.json")
    md_out = Path(args.md_out) if args.md_out else (Path(__file__).resolve().parents[1] / "infra" / "governance" / f"LICENSE_AUDIT_REPORT_{date_tag}.md")
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    md_out.write_text(to_markdown(report), encoding="utf-8")
    print(json.dumps({"status": "ok", "json_out": str(json_out), "md_out": str(md_out), "repo_count": len(rows)}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
