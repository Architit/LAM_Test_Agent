from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lam_test_agent_paths import lam_root as default_lam_root
from lam_test_agent_paths import workspace_root


DEFAULT_SCAN_FILES = (
    "DEV_LOGS.md",
    "ROADMAP.md",
    "TASK_LIST.md",
    "WORKFLOW_SNAPSHOT_STATE.md",
    "INTERACTION_PROTOCOL.md",
)

STATE_RE = re.compile(
    r"HOLD_BY_DEADLOOP_BREAK_PROTOCOL|HOLD|PASS|OPEN_[A-Z0-9_]+|OPEN|RESUME|S27|S28",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class AbabCycle:
    token_a: str
    token_b: str
    tail_length: int
    sequence: list[str]


def _load_pattern_module(lam_root: Path) -> Any:
    mod_path = lam_root / "src" / "deadloop_patterns.py"
    spec = importlib.util.spec_from_file_location("lam_deadloop_patterns", mod_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load: {mod_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _discover_repos(root: Path) -> list[Path]:
    repos: set[Path] = set()
    resolved = root.resolve()
    if (resolved / ".git").exists():
        repos.add(resolved)
    repos.update(p.parent.resolve() for p in resolved.glob("*/.git") if p.exists())
    repos.update(p.parent.resolve() for p in resolved.glob("*/*/.git") if p.exists())
    return sorted(repos)


def _scan_lines_for_hits(lines: list[str], pattern_mod: Any) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for hit in pattern_mod.scan_text_for_patterns(lines):
        hits.append(
            {
                "pattern_id": hit.pattern_id,
                "severity": hit.severity,
                "line_no": hit.line_no,
                "line": hit.line,
            }
        )
    return hits


def _extract_state_tokens(lines: list[str]) -> list[str]:
    tokens: list[str] = []
    for line in lines:
        for match in STATE_RE.findall(line):
            tokens.append(match.upper())
    return tokens


def _detect_abab_tail(tokens: list[str], min_len: int = 6) -> AbabCycle | None:
    if len(tokens) < min_len:
        return None
    max_len = len(tokens) if len(tokens) % 2 == 0 else len(tokens) - 1
    for length in range(max_len, min_len - 1, -2):
        tail = tokens[-length:]
        a, b = tail[0], tail[1]
        if a == b:
            continue
        valid = True
        for idx, token in enumerate(tail):
            expected = a if idx % 2 == 0 else b
            if token != expected:
                valid = False
                break
        if valid:
            return AbabCycle(token_a=a, token_b=b, tail_length=length, sequence=tail)
    return None


def _scan_repo(repo: Path, files: tuple[str, ...], pattern_mod: Any) -> dict[str, Any]:
    all_hits: list[dict[str, Any]] = []
    all_tokens: list[str] = []
    scanned_files: list[str] = []
    for rel in files:
        fp = repo / rel
        if not fp.exists() or not fp.is_file():
            continue
        scanned_files.append(rel)
        lines = fp.read_text(encoding="utf-8", errors="ignore").splitlines()
        all_hits.extend(_scan_lines_for_hits(lines, pattern_mod))
        all_tokens.extend(_extract_state_tokens(lines))

    severity_counts = Counter(hit["severity"] for hit in all_hits)
    pattern_counts = Counter(hit["pattern_id"] for hit in all_hits)
    abab = _detect_abab_tail(all_tokens)

    risk_score = (
        severity_counts.get("critical", 0) * 5
        + severity_counts.get("high", 0) * 3
        + severity_counts.get("medium", 0) * 2
        + severity_counts.get("low", 0)
    )
    if abab is not None:
        risk_score += 10 + abab.tail_length

    return {
        "repo": str(repo),
        "repo_name": repo.name,
        "scanned_files": scanned_files,
        "hit_count": len(all_hits),
        "severity_counts": dict(severity_counts),
        "pattern_counts": dict(pattern_counts),
        "abab_tail_cycle": asdict(abab) if abab is not None else None,
        "risk_score": risk_score,
    }


def collect_snapshot(root: Path, lam_root: Path, files: tuple[str, ...]) -> dict[str, Any]:
    pattern_mod = _load_pattern_module(lam_root)
    repos = _discover_repos(root)
    rows = [_scan_repo(repo, files, pattern_mod) for repo in repos]
    rows.sort(key=lambda row: row["risk_score"], reverse=True)

    repos_with_abab = sum(1 for row in rows if row["abab_tail_cycle"] is not None)
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "ecosystem_root": str(root),
        "lam_root": str(lam_root),
        "files": list(files),
        "summary": {
            "repo_count": len(rows),
            "repos_with_hits": sum(1 for row in rows if row["hit_count"] > 0),
            "repos_with_abab_tail_cycle": repos_with_abab,
            "max_risk_score": rows[0]["risk_score"] if rows else 0,
        },
        "repos": rows,
    }


def render_markdown(snapshot: dict[str, Any]) -> str:
    lines = [
        "# DEADLOOP_GLOBAL_TELEMETRY",
        "",
        f"- generated_at_utc: {snapshot['generated_at_utc']}",
        f"- ecosystem_root: {snapshot['ecosystem_root']}",
        f"- lam_root: {snapshot['lam_root']}",
        f"- files: {', '.join(snapshot['files'])}",
        "",
        "## Summary",
        f"- repo_count: {snapshot['summary']['repo_count']}",
        f"- repos_with_hits: {snapshot['summary']['repos_with_hits']}",
        f"- repos_with_abab_tail_cycle: {snapshot['summary']['repos_with_abab_tail_cycle']}",
        f"- max_risk_score: {snapshot['summary']['max_risk_score']}",
        "",
        "## Risk Top 10",
        "| Repo | Risk | Hits | Critical | High | Medium | ABAB tail |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in snapshot["repos"][:10]:
        sev = row["severity_counts"]
        abab = row["abab_tail_cycle"]
        abab_text = "-"
        if abab is not None:
            abab_text = f"{abab['token_a']}/{abab['token_b']} x{abab['tail_length']}"
        lines.append(
            f"| {row['repo_name']} | {row['risk_score']} | {row['hit_count']} | "
            f"{sev.get('critical', 0)} | {sev.get('high', 0)} | {sev.get('medium', 0)} | {abab_text} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_outputs(snapshot: dict[str, Any], json_output: Path, md_output: Path) -> None:
    json_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(snapshot, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    md_output.write_text(render_markdown(snapshot) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Global deadloop telemetry + ABAB tail-cycle detection.")
    parser.add_argument("--root", default=str(workspace_root()))
    parser.add_argument("--lam-root", default=str(default_lam_root()))
    parser.add_argument(
        "--json-output",
        default="memory/FRONT/DEADLOOP_GLOBAL_TELEMETRY.json",
    )
    parser.add_argument(
        "--md-output",
        default="memory/FRONT/DEADLOOP_GLOBAL_TELEMETRY.md",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    lam_root = Path(args.lam_root).resolve()
    if not root.exists():
        print(f"DEADLOOP_TELEMETRY_FAIL: root not found: {root}")
        return 2
    if not lam_root.exists():
        print(f"DEADLOOP_TELEMETRY_FAIL: lam root not found: {lam_root}")
        return 2

    snapshot = collect_snapshot(root=root, lam_root=lam_root, files=DEFAULT_SCAN_FILES)
    write_outputs(snapshot, Path(args.json_output), Path(args.md_output))
    print(
        "DEADLOOP_TELEMETRY_OK "
        f"repos={snapshot['summary']['repo_count']} "
        f"abab={snapshot['summary']['repos_with_abab_tail_cycle']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
