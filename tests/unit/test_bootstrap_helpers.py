from __future__ import annotations

from pathlib import Path
import sys

import pytest

from lam_test_agent_bootstrap import (
    agent_src_paths,
    extend_agent_sys_path,
    missing_agent_src_paths,
    missing_paths_as_text,
    repo_root,
)


@pytest.mark.unit
def test_repo_root_returns_parent_dir(tmp_path: Path) -> None:
    f = tmp_path / "nested" / "file.py"
    f.parent.mkdir(parents=True)
    f.write_text("x", encoding="utf-8")
    assert repo_root(f) == f.resolve().parent


@pytest.mark.unit
def test_agent_src_paths_returns_two_expected_paths(tmp_path: Path) -> None:
    paths = agent_src_paths(tmp_path)
    assert len(paths) == 2
    assert paths[0].as_posix().endswith("LAM_Test/agents/codex-agent/src")
    assert paths[1].as_posix().endswith("LAM_Test/agents/comm-agent/src")


@pytest.mark.unit
def test_missing_agent_src_paths_reports_both_when_absent(tmp_path: Path) -> None:
    missing = missing_agent_src_paths(tmp_path)
    assert len(missing) == 2


@pytest.mark.unit
def test_missing_agent_src_paths_reports_none_when_present(tmp_path: Path) -> None:
    for p in agent_src_paths(tmp_path):
        p.mkdir(parents=True)
    assert missing_agent_src_paths(tmp_path) == []


@pytest.mark.unit
def test_extend_agent_sys_path_adds_paths_once(tmp_path: Path) -> None:
    initial_len = len(sys.path)
    extend_agent_sys_path(tmp_path)
    first_len = len(sys.path)
    extend_agent_sys_path(tmp_path)
    second_len = len(sys.path)
    assert first_len == second_len
    assert second_len >= initial_len


@pytest.mark.unit
def test_missing_paths_as_text_is_joined_string(tmp_path: Path) -> None:
    p1 = tmp_path / "a"
    p2 = tmp_path / "b"
    out = missing_paths_as_text([p1, p2])
    assert str(p1) in out and str(p2) in out
