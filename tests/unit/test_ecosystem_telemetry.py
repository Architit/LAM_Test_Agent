from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from lam_test_agent_ecosystem_telemetry import (
    RepoTelemetry,
    discover_repos,
    evaluate_archivator_handoff,
    evaluate_semantic_identity_health,
    render_markdown,
    write_files,
)


@pytest.mark.unit
def test_discover_repos_finds_git_dirs(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir(parents=True)
    (tmp_path / "A" / ".git").mkdir(parents=True)
    (tmp_path / "B" / "C" / ".git").mkdir(parents=True)
    repos = discover_repos(tmp_path, max_depth=2)
    names = {p.name for p in repos}
    assert tmp_path.name in names
    assert "A" in names
    assert "C" in names


@pytest.mark.unit
def test_discover_repos_accepts_git_file_layout(tmp_path: Path) -> None:
    repo = tmp_path / "SubmoduleLike"
    repo.mkdir(parents=True)
    (repo / ".git").write_text("gitdir: /tmp/example", encoding="utf-8")

    repos = discover_repos(tmp_path, max_depth=2)
    names = {p.name for p in repos}
    assert "SubmoduleLike" in names


@pytest.mark.unit
def test_render_markdown_contains_summary_and_table() -> None:
    snap = {
        "generated_at_utc": "2026-02-17T00:00:00Z",
        "root": "/tmp/root",
        "summary": {
            "repo_count": 1,
            "dirty_repos": 0,
            "repos_with_tests": 1,
            "repos_with_ci": 1,
            "repos_with_governance_triad": 1,
            "repos_with_submodules": 0,
        },
        "repos": [
            {
                "repo_name": "X",
                "branch": "main",
                "dirty": False,
                "ahead": 0,
                "behind": 0,
                "has_tests_dir": True,
                "has_ci_workflows": True,
                "has_roadmap": True,
                "has_dev_logs": True,
                "has_interaction_protocol": True,
                "submodule_count": 0,
            }
        ],
    }
    text = render_markdown(snap)
    assert "## Summary" in text
    assert "| Repo | Branch | Dirty |" in text


@pytest.mark.unit
def test_write_files_writes_both_formats(tmp_path: Path) -> None:
    snap = {
        "generated_at_utc": "2026-02-17T00:00:00Z",
        "root": "/tmp/root",
        "summary": {
            "repo_count": 0,
            "dirty_repos": 0,
            "repos_with_tests": 0,
            "repos_with_ci": 0,
            "repos_with_governance_triad": 0,
            "repos_with_submodules": 0,
        },
        "repos": [],
    }
    j = tmp_path / "a.json"
    m = tmp_path / "a.md"
    write_files(snap, j, m)
    assert json.loads(j.read_text(encoding="utf-8"))["summary"]["repo_count"] == 0
    assert "# ECOSYSTEM_TELEMETRY_SNAPSHOT" in m.read_text(encoding="utf-8")


def _repo(name: str, path: Path) -> RepoTelemetry:
    return RepoTelemetry(
        repo_name=name,
        repo_path=str(path),
        branch="main",
        dirty=False,
        modified_entries=0,
        untracked_entries=0,
        ahead=0,
        behind=0,
        last_commit="h",
        last_commit_utc="2026-02-17T00:00:00Z",
        remotes=["origin"],
        submodule_count=0,
        has_tests_dir=True,
        has_pytest_ini=True,
        has_dev_requirements=True,
        has_ci_workflows=True,
        has_roadmap=True,
        has_dev_logs=True,
        has_interaction_protocol=True,
    )


@pytest.mark.unit
def test_evaluate_archivator_handoff_detects_missing_and_stale(tmp_path: Path) -> None:
    archivator = tmp_path / "Archivator_Agent"
    mirror_root = archivator / "SubtreeHub" / "repos"
    mirror_root.mkdir(parents=True)

    source_a = tmp_path / "RepoA"
    source_a.mkdir()
    (source_a / "WORKFLOW_SNAPSHOT_STATE.md").write_text("new", encoding="utf-8")

    source_b = tmp_path / "RepoB"
    source_b.mkdir()
    (source_b / "WORKFLOW_SNAPSHOT_STATE.md").write_text("new", encoding="utf-8")

    (mirror_root / "RepoA").mkdir(parents=True)
    (mirror_root / "RepoA" / "WORKFLOW_SNAPSHOT_STATE.md").write_text("old", encoding="utf-8")
    source_file = source_a / "WORKFLOW_SNAPSHOT_STATE.md"
    mirror_file = mirror_root / "RepoA" / "WORKFLOW_SNAPSHOT_STATE.md"
    # Force deterministic stale ordering independent of filesystem timestamp granularity.
    os.utime(mirror_file, (1000, 1000))
    os.utime(source_file, (5000, 5000))

    rows = [_repo("Archivator_Agent", archivator), _repo("RepoA", source_a), _repo("RepoB", source_b)]
    handoff = evaluate_archivator_handoff(rows)
    assert handoff["scope_active"] is True
    assert handoff["handoff_ok"] is False
    assert "RepoA" in handoff["stale_mirrors"]
    assert "RepoB" in handoff["missing_mirrors"]


@pytest.mark.unit
def test_evaluate_semantic_identity_health_detects_template_and_provisional(tmp_path: Path) -> None:
    target = tmp_path / "memory" / "FRONT"
    target.mkdir(parents=True)
    (target / "SEMANTIC_IDENTITY_MAP_PHASE3_2026-02-17.tsv").write_text(
        (
            "repo\tentity_scope\ttrue_name\tcall_sign\tsystem_id\tsubtree_prefix\tstatus\tsource_evidence\n"
            "/tmp/SubtreeHub\trepo_domain\tSubtreeHubshpoisat\tSubtreeHub\tSUBTREEHUB\tSUBTREEHUB/SubtreeHub\tACTIVE_PROVISIONAL\tGOVERNANCE_PROVISIONAL_RULE_V1\n"
        ),
        encoding="utf-8",
    )
    result = evaluate_semantic_identity_health(tmp_path)
    assert result["scope_active"] is True
    assert result["identity_ok"] is False
    assert result["provisional_count"] >= 1
    assert result["templated_true_name_count"] >= 1
    assert len(result["violations"]) >= 2


@pytest.mark.unit
def test_evaluate_semantic_identity_health_uses_latest_realtime_file(tmp_path: Path) -> None:
    target = tmp_path / "memory" / "FRONT"
    target.mkdir(parents=True)
    older = target / "SEMANTIC_IDENTITY_MAP_2026-02-17.tsv"
    newer = target / "SEMANTIC_IDENTITY_MAP_2026-02-18.tsv"

    older.write_text(
        (
            "repo\tentity_scope\ttrue_name\tcall_sign\tsystem_id\tsubtree_prefix\tstatus\tsource_evidence\n"
            "x\trepo_domain\tUNRESOLVED_TRUE_NAME\tSubtreeHub\tSUBTREEHUB\tSUBTREEHUB/SubtreeHub\tHOLD\tPENDING_GOVERNANCE_MAPPING\n"
        ),
        encoding="utf-8",
    )
    newer.write_text(
        (
            "repo\tentity_scope\ttrue_name\tcall_sign\tsystem_id\tsubtree_prefix\tstatus\tsource_evidence\n"
            "x\trepo_domain\tSubtreeHub\tSubtreeHub\tSUBTREEHUB\tSUBTREEHUB/SubtreeHub\tACTIVE\tGOVERNANCE_RULE_V2\n"
        ),
        encoding="utf-8",
    )
    os.utime(older, (1000, 1000))
    os.utime(newer, (5000, 5000))

    result = evaluate_semantic_identity_health(tmp_path)
    assert result["identity_ok"] is True
    assert str(newer) in result["checked_files"]
    assert str(older) not in result["checked_files"]
