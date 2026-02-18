from __future__ import annotations

import re
from pathlib import Path

from lam_test_agent_route_matrix import SCENARIO_ROUTE_IDS


ROUTE_ID_RE = re.compile(r"^\|\s*(R-\d{3})\s*\|")
ROUTE_STATUS_RE = re.compile(r"^\|\s*(R-\d{3})\s*\|.*\|\s*(active|planned)\s*\|$", re.IGNORECASE)


def route_ids_from_matrix_file(path: Path) -> set[str]:
    route_ids: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        m = ROUTE_ID_RE.match(line)
        if m:
            route_ids.add(m.group(1))
    return route_ids


def route_ids_from_mapping() -> set[str]:
    out: set[str] = set()
    for ids in SCENARIO_ROUTE_IDS.values():
        out.update(ids)
    return out


def route_statuses_from_matrix_file(path: Path) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = ROUTE_STATUS_RE.match(line.strip())
        if m:
            statuses[m.group(1)] = m.group(2).lower()
    return statuses
