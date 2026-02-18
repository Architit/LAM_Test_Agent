from __future__ import annotations

from pathlib import Path
import sys
from typing import Iterable


def repo_root(from_path: str | Path) -> Path:
    return Path(from_path).resolve().parent


def agent_src_paths(root: Path) -> list[Path]:
    return [
        root / "LAM_Test" / "agents" / "codex-agent" / "src",
        root / "LAM_Test" / "agents" / "comm-agent" / "src",
    ]


def missing_agent_src_paths(root: Path) -> list[Path]:
    return [p for p in agent_src_paths(root) if not p.exists()]


def extend_agent_sys_path(root: Path) -> None:
    # Ensure comm-agent paths win for shared top-level module names (e.g. interfaces, agents).
    paths = agent_src_paths(root)
    preferred = [paths[0], paths[1]]
    for path in preferred:
        s = str(path)
        if s not in sys.path:
            sys.path.insert(0, s)


def missing_paths_as_text(paths: Iterable[Path]) -> str:
    return ", ".join(str(p) for p in paths)
