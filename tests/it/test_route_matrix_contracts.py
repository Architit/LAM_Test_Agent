from __future__ import annotations

from pathlib import Path

import pytest

from lam_test_agent_contracts import is_valid_trace_id
from lam_test_agent_route_matrix import (
    execute_scenario_with_mock,
    execute_scenario_with_provider_outage,
    execution_result_to_payload,
    normalize_execution_payload,
)
from lam_test_agent_scenarios import load_scenarios


ROOT = Path(__file__).resolve().parents[2]
SPECS = load_scenarios(ROOT)


pytestmark = [pytest.mark.integration, pytest.mark.route]


@pytest.mark.parametrize("spec", SPECS, ids=lambda s: s.scenario_id)
def test_route_execution_payload_roundtrip_contract(spec) -> None:
    result = execute_scenario_with_mock(spec)
    payload = execution_result_to_payload(result)
    normalized = normalize_execution_payload(payload)

    assert normalized.scenario_id == spec.scenario_id
    assert normalized.status == spec.expected_status
    assert is_valid_trace_id(normalized.trace_id)
    assert all(h.trace_id == normalized.trace_id for h in normalized.hops)


@pytest.mark.parametrize("spec", SPECS, ids=lambda s: s.scenario_id)
def test_route_execution_provider_outage_degrades(spec) -> None:
    result = execute_scenario_with_provider_outage(spec)
    payload = execution_result_to_payload(result)
    normalized = normalize_execution_payload(payload)

    assert normalized.status == "degraded"
    assert normalized.fallback_used
    assert normalized.reason == "provider_unavailable"


@pytest.mark.parametrize(
    "payload,expected",
    [
        ({}, "missing field: scenario_id"),
        (
            {
                "scenario_id": "x",
                "expected_status": "ok",
                "status": "ok",
                "fallback_used": False,
                "trace_id": "trace-x",
                "hops": [],
            },
            "hops must be non-empty list",
        ),
        (
            {
                "scenario_id": "x",
                "expected_status": "ok",
                "status": "ok",
                "fallback_used": False,
                "trace_id": "bad trace",
                "hops": [{"route_id": "R-001", "source": "a", "target": "b", "layer": "agent", "status": "ok", "trace_id": "trace-x"}],
            },
            "trace_id has invalid format",
        ),
    ],
)
def test_route_execution_payload_rejects_invalid_envelope(payload, expected: str) -> None:
    with pytest.raises(ValueError, match=expected):
        normalize_execution_payload(payload)
