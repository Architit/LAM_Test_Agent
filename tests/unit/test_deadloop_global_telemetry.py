from __future__ import annotations

from pathlib import Path

import pytest

from lam_test_agent_deadloop_global_telemetry import _discover_repos, main as deadloop_global_main


@pytest.mark.unit
def test_discover_repos_includes_root_and_nested_git_dirs(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir(parents=True)
    (tmp_path / "A" / ".git").mkdir(parents=True)
    (tmp_path / "B" / "C" / ".git").mkdir(parents=True)

    repos = _discover_repos(tmp_path)
    names = {p.name for p in repos}
    assert tmp_path.name in names
    assert "A" in names
    assert "C" in names


@pytest.mark.unit
def test_discover_repos_accepts_git_file_layout(tmp_path: Path) -> None:
    repo = tmp_path / "SubmoduleLike"
    repo.mkdir(parents=True)
    (repo / ".git").write_text("gitdir: /tmp/example", encoding="utf-8")

    repos = _discover_repos(tmp_path)
    names = {p.name for p in repos}
    assert "SubmoduleLike" in names


@pytest.mark.unit
def test_deadloop_global_main_returns_code_2_when_pattern_module_missing(tmp_path: Path) -> None:
    root = tmp_path / "ecosystem"
    lam_root = tmp_path / "LAM"
    root.mkdir(parents=True)
    lam_root.mkdir(parents=True)

    rc = deadloop_global_main(
        [
            "--root",
            str(root),
            "--lam-root",
            str(lam_root),
            "--json-output",
            str(tmp_path / "out.json"),
            "--md-output",
            str(tmp_path / "out.md"),
        ]
    )
    assert rc == 2
