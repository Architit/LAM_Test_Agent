from __future__ import annotations

from pathlib import Path

import pytest

from lam_test_agent_route_matrix import execute_scenario_with_mock, route_ids_for_scenario
from lam_test_agent_scenarios import load_scenarios


ROOT = Path(__file__).resolve().parents[2]
SPECS = load_scenarios(ROOT)


pytestmark = [pytest.mark.integration, pytest.mark.route]


@pytest.mark.parametrize("spec", SPECS, ids=lambda s: s.scenario_id)
def test_route_matrix_scenario_executes_with_mock(spec) -> None:
    result = execute_scenario_with_mock(spec)
    assert result.status == spec.expected_status
    assert len(result.hops) == len(spec.routes)
    assert all(h.trace_id == result.trace_id for h in result.hops)

    if spec.expected_status == "degraded":
        assert result.fallback_used
        assert result.reason == "provider_unavailable"
    else:
        assert not result.fallback_used
        assert result.reason is None


@pytest.mark.integration
def test_route_matrix_covers_all_route_ids() -> None:
    covered: set[str] = set()
    for spec in SPECS:
        covered.update(route_ids_for_scenario(spec))
    assert covered == {"R-001", "R-002", "R-003", "R-004", "R-005", "R-006", "R-007", "R-008"}
