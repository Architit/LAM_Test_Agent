from __future__ import annotations

from pathlib import Path

import pytest

from lam_test_agent_matrix_sync import (
    route_ids_from_mapping,
    route_ids_from_matrix_file,
    route_statuses_from_matrix_file,
)


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.unit
def test_route_matrix_markdown_is_synced_with_mapping() -> None:
    markdown_ids = route_ids_from_matrix_file(ROOT / "TEST_MIRROR_MATRIX.md")
    mapping_ids = route_ids_from_mapping()
    assert markdown_ids == mapping_ids


@pytest.mark.unit
def test_route_matrix_statuses_match_route_coverage_state() -> None:
    statuses = route_statuses_from_matrix_file(ROOT / "TEST_MIRROR_MATRIX.md")
    mapped = route_ids_from_mapping()

    assert set(statuses) == mapped

    # All mapped routes are executed by integration route-matrix suites,
    # so matrix status must stay "active".
    for route_id in mapped:
        assert statuses[route_id] == "active"
