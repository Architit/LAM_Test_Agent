from __future__ import annotations

from pathlib import Path

import pytest

from lam_test_agent_deadloop_global_telemetry import _discover_repos


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
