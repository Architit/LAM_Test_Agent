from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lam_test_agent_bootstrap import missing_agent_src_paths, repo_root  # noqa: E402


ROOT = repo_root(__file__).parent
MISSING_AGENT_PATHS = missing_agent_src_paths(ROOT)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if not MISSING_AGENT_PATHS:
        return
    reason = (
        "submodule-dependent test skipped; missing agent sources: "
        + ", ".join(str(p) for p in MISSING_AGENT_PATHS)
    )
    skip_marker = pytest.mark.skip(reason=reason)
    for item in items:
        if item.get_closest_marker("submodule_required"):
            item.add_marker(skip_marker)
