from __future__ import annotations

from pathlib import Path

import pytest

import lam_test_agent_paths as paths


@pytest.mark.unit
def test_workspace_root_prefers_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    custom = tmp_path / "custom_root"
    custom.mkdir(parents=True)
    monkeypatch.setenv("LAM_WORKSPACE_ROOT", str(custom))
    assert paths.workspace_root() == custom.resolve()


@pytest.mark.unit
def test_workspace_root_discovers_ancestor_with_lam(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    root = tmp_path / "ecosystem"
    nested_repo = root / "a" / "b" / "test-agent"
    (root / "LAM").mkdir(parents=True)
    nested_repo.mkdir(parents=True)

    monkeypatch.delenv("LAM_WORKSPACE_ROOT", raising=False)
    monkeypatch.setattr(paths, "repo_root", lambda: nested_repo)

    assert paths.workspace_root() == root.resolve()
