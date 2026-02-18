from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parent


def workspace_root() -> Path:
    raw = os.getenv("LAM_WORKSPACE_ROOT", "")
    if raw:
        return Path(raw).expanduser().resolve()
    return repo_root().parent


def lam_root() -> Path:
    raw = os.getenv("LAM_ROOT", "")
    if raw:
        return Path(raw).expanduser().resolve()
    return workspace_root() / "LAM"


def sibling_repo(repo_name: str) -> Path:
    return workspace_root() / repo_name
