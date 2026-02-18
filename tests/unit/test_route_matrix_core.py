from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from lam_test_agent_route_matrix import (
    RouteExecutionResult,
    RouteHopResult,
    execute_scenario_with_mock,
    execute_scenario_with_provider_outage,
    execution_result_to_payload,
    normalize_execution_payload,
    route_ids_for_scenario,
    validate_execution_invariants,
)
from lam_test_agent_scenarios import ScenarioSpec, load_scenarios


ROOT = Path(__file__).resolve().parents[2]
SPECS = load_scenarios(ROOT)


@pytest.mark.unit
def test_route_ids_count_matches_scenario_routes() -> None:
    for spec in SPECS:
        assert len(route_ids_for_scenario(spec)) == len(spec.routes)


@pytest.mark.unit
def test_route_ids_for_unknown_scenario_raises() -> None:
    spec = ScenarioSpec(
        scenario_id="unknown",
        title="x",
        routes=tuple(),
        required_contracts=("x",),
        expected_status="ok",
    )
    with pytest.raises(ValueError, match="unknown scenario_id"):
        route_ids_for_scenario(spec)


@pytest.mark.unit
def test_execute_scenario_with_mock_produces_consistent_trace() -> None:
    spec = next(s for s in SPECS if s.scenario_id == "scn_codex_comm_ping_pong")
    result = execute_scenario_with_mock(spec)
    assert result.status == "ok"
    assert all(h.trace_id == result.trace_id for h in result.hops)


@pytest.mark.unit
def test_execute_scenario_with_provider_outage_sets_degraded() -> None:
    spec = next(s for s in SPECS if s.scenario_id == "scn_comm_roaudter_fallback")
    result = execute_scenario_with_provider_outage(spec)
    assert result.status == "degraded"
    assert result.fallback_used
    assert result.reason == "provider_unavailable"
    assert any(h.status == "error" for h in result.hops)


@pytest.mark.unit
def test_normalize_execution_payload_roundtrip() -> None:
    spec = next(s for s in SPECS if s.scenario_id == "scn_taskarid_chain_route")
    payload = execution_result_to_payload(execute_scenario_with_mock(spec))
    out = normalize_execution_payload(payload)
    assert out.scenario_id == spec.scenario_id
    assert len(out.hops) == len(spec.routes)


@pytest.mark.unit
def test_validate_execution_invariants_accepts_valid_result() -> None:
    spec = next(s for s in SPECS if s.scenario_id == "scn_codex_comm_ping_pong")
    result = execute_scenario_with_mock(spec)
    assert validate_execution_invariants(result) == []


@pytest.mark.unit
def test_validate_execution_invariants_rejects_trace_break() -> None:
    spec = next(s for s in SPECS if s.scenario_id == "scn_codex_comm_ping_pong")
    result = execute_scenario_with_mock(spec)
    hops = list(result.hops)
    hops[0] = replace(hops[0], trace_id="trace-other")
    broken = RouteExecutionResult(
        scenario_id=result.scenario_id,
        expected_status=result.expected_status,
        status=result.status,
        reason=result.reason,
        fallback_used=result.fallback_used,
        trace_id=result.trace_id,
        hops=tuple(hops),
    )
    assert "trace continuity violated across route hops" in validate_execution_invariants(broken)


@pytest.mark.unit
def test_validate_execution_invariants_rejects_degraded_without_reason() -> None:
    bad = RouteExecutionResult(
        scenario_id="s",
        expected_status="degraded",
        status="degraded",
        reason=None,
        fallback_used=False,
        trace_id="trace-s",
        hops=(
            RouteHopResult(
                route_id="R-001",
                source="a",
                target="b",
                layer="agent",
                status="ok",
                trace_id="trace-s",
            ),
        ),
    )
    errors = validate_execution_invariants(bad)
    assert "degraded status requires fallback_used=true" in errors
    assert "degraded status requires non-empty reason" in errors
