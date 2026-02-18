from __future__ import annotations

from pathlib import Path

import pytest

from lam_test_agent_route_matrix import (
    execute_scenario_with_provider_outage,
    execution_result_to_payload,
    normalize_execution_payload,
    validate_execution_invariants,
)
from lam_test_agent_scenarios import load_scenarios


ROOT = Path(__file__).resolve().parents[2]
SPECS = load_scenarios(ROOT)


pytestmark = [pytest.mark.integration, pytest.mark.route]


@pytest.mark.parametrize("spec", SPECS, ids=lambda s: s.scenario_id)
def test_failure_topology_trace_break_detected(spec) -> None:
    payload = execution_result_to_payload(execute_scenario_with_provider_outage(spec))
    payload["hops"][0]["trace_id"] = "trace-mismatch"
    normalized = normalize_execution_payload(payload)

    errors = validate_execution_invariants(normalized)
    assert "trace continuity violated across route hops" in errors


@pytest.mark.parametrize("spec", SPECS, ids=lambda s: s.scenario_id)
def test_failure_topology_degraded_without_fallback_detected(spec) -> None:
    payload = execution_result_to_payload(execute_scenario_with_provider_outage(spec))
    payload["fallback_used"] = False
    normalized = normalize_execution_payload(payload)

    errors = validate_execution_invariants(normalized)
    assert "degraded status requires fallback_used=true" in errors
    assert "provider_unavailable reason requires fallback_used=true" in errors


@pytest.mark.parametrize("spec", SPECS, ids=lambda s: s.scenario_id)
def test_failure_topology_provider_unavailable_with_error_status_detected(spec) -> None:
    payload = execution_result_to_payload(execute_scenario_with_provider_outage(spec))
    payload["status"] = "error"
    payload["fallback_used"] = False
    normalized = normalize_execution_payload(payload)

    errors = validate_execution_invariants(normalized)
    assert "provider_unavailable reason requires degraded status" in errors
