from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, Mapping

from lam_test_agent_contracts import is_valid_trace_id
from lam_test_agent_scenarios import ScenarioSpec


SCENARIO_ROUTE_IDS: Final[dict[str, tuple[str, ...]]] = {
    "scn_codex_comm_ping_pong": ("R-001", "R-002"),
    "scn_comm_roaudter_fallback": ("R-003", "R-004", "R-005"),
    "scn_taskarid_chain_route": ("R-006", "R-007", "R-007", "R-008"),
}


@dataclass(frozen=True)
class RouteHopResult:
    route_id: str
    source: str
    target: str
    layer: str
    status: str
    trace_id: str


@dataclass(frozen=True)
class RouteExecutionResult:
    scenario_id: str
    expected_status: str
    status: str
    reason: str | None
    fallback_used: bool
    trace_id: str
    hops: tuple[RouteHopResult, ...]


def route_ids_for_scenario(spec: ScenarioSpec) -> tuple[str, ...]:
    route_ids = SCENARIO_ROUTE_IDS.get(spec.scenario_id)
    if route_ids is None:
        raise ValueError(f"unknown scenario_id for route id mapping: {spec.scenario_id}")
    if len(route_ids) != len(spec.routes):
        raise ValueError(
            f"route id count mismatch for {spec.scenario_id}: "
            f"{len(route_ids)} ids for {len(spec.routes)} routes"
        )
    return route_ids


def execute_scenario_with_mock(spec: ScenarioSpec) -> RouteExecutionResult:
    route_ids = route_ids_for_scenario(spec)
    trace_id = f"trace-{spec.scenario_id}"
    if not is_valid_trace_id(trace_id):
        raise ValueError(f"generated trace_id is invalid: {trace_id}")

    hops: list[RouteHopResult] = []
    for route_id, route in zip(route_ids, spec.routes):
        hops.append(
            RouteHopResult(
                route_id=route_id,
                source=route.source,
                target=route.target,
                layer=route.layer,
                status="ok",
                trace_id=trace_id,
            )
        )

    status = spec.expected_status
    fallback_used = status == "degraded"
    reason = "provider_unavailable" if fallback_used else None

    return RouteExecutionResult(
        scenario_id=spec.scenario_id,
        expected_status=spec.expected_status,
        status=status,
        reason=reason,
        fallback_used=fallback_used,
        trace_id=trace_id,
        hops=tuple(hops),
    )


def execute_scenario_with_provider_outage(spec: ScenarioSpec) -> RouteExecutionResult:
    route_ids = route_ids_for_scenario(spec)
    trace_id = f"trace-{spec.scenario_id}-outage"
    if not is_valid_trace_id(trace_id):
        raise ValueError(f"generated trace_id is invalid: {trace_id}")

    hops: list[RouteHopResult] = []
    for route_id, route in zip(route_ids, spec.routes):
        hop_status = "error" if route.layer == "ecosystem" else "ok"
        hops.append(
            RouteHopResult(
                route_id=route_id,
                source=route.source,
                target=route.target,
                layer=route.layer,
                status=hop_status,
                trace_id=trace_id,
            )
        )

    return RouteExecutionResult(
        scenario_id=spec.scenario_id,
        expected_status=spec.expected_status,
        status="degraded",
        reason="provider_unavailable",
        fallback_used=True,
        trace_id=trace_id,
        hops=tuple(hops),
    )


def execution_result_to_payload(result: RouteExecutionResult) -> dict[str, Any]:
    return {
        "scenario_id": result.scenario_id,
        "expected_status": result.expected_status,
        "status": result.status,
        "reason": result.reason,
        "fallback_used": result.fallback_used,
        "trace_id": result.trace_id,
        "hops": [
            {
                "route_id": h.route_id,
                "source": h.source,
                "target": h.target,
                "layer": h.layer,
                "status": h.status,
                "trace_id": h.trace_id,
            }
            for h in result.hops
        ],
    }


def normalize_execution_payload(raw: Mapping[str, Any]) -> RouteExecutionResult:
    required = (
        "scenario_id",
        "expected_status",
        "status",
        "fallback_used",
        "trace_id",
        "hops",
    )
    for field in required:
        if field not in raw:
            raise ValueError(f"missing field: {field}")

    scenario_id = raw["scenario_id"]
    expected_status = raw["expected_status"]
    status = raw["status"]
    fallback_used = raw["fallback_used"]
    trace_id = raw["trace_id"]
    hops_raw = raw["hops"]

    if not isinstance(scenario_id, str) or not scenario_id.strip():
        raise ValueError("scenario_id must be non-empty string")
    if expected_status not in {"ok", "error", "degraded"}:
        raise ValueError("expected_status must be one of: ok,error,degraded")
    if status not in {"ok", "error", "degraded"}:
        raise ValueError("status must be one of: ok,error,degraded")
    if not isinstance(fallback_used, bool):
        raise ValueError("fallback_used must be bool")
    if not is_valid_trace_id(trace_id):
        raise ValueError("trace_id has invalid format")
    if not isinstance(hops_raw, list) or len(hops_raw) == 0:
        raise ValueError("hops must be non-empty list")

    hops: list[RouteHopResult] = []
    for i, hop in enumerate(hops_raw):
        if not isinstance(hop, Mapping):
            raise ValueError(f"hop[{i}] must be mapping")
        for key in ("route_id", "source", "target", "layer", "status", "trace_id"):
            if key not in hop:
                raise ValueError(f"hop[{i}] missing {key}")
        route_id = hop["route_id"]
        source = hop["source"]
        target = hop["target"]
        layer = hop["layer"]
        hop_status = hop["status"]
        hop_trace_id = hop["trace_id"]
        if not all(isinstance(v, str) and v.strip() for v in (route_id, source, target, layer, hop_status)):
            raise ValueError(f"hop[{i}] fields must be non-empty strings")
        if not is_valid_trace_id(hop_trace_id):
            raise ValueError(f"hop[{i}] trace_id has invalid format")
        hops.append(
            RouteHopResult(
                route_id=route_id,
                source=source,
                target=target,
                layer=layer,
                status=hop_status,
                trace_id=hop_trace_id,
            )
        )

    reason = raw.get("reason")
    if reason is not None and (not isinstance(reason, str) or not reason.strip()):
        raise ValueError("reason must be non-empty string when provided")

    return RouteExecutionResult(
        scenario_id=scenario_id,
        expected_status=expected_status,
        status=status,
        reason=reason,
        fallback_used=fallback_used,
        trace_id=trace_id,
        hops=tuple(hops),
    )


def validate_execution_invariants(result: RouteExecutionResult) -> list[str]:
    errors: list[str] = []

    if any(h.trace_id != result.trace_id for h in result.hops):
        errors.append("trace continuity violated across route hops")

    if result.status == "degraded":
        if not result.fallback_used:
            errors.append("degraded status requires fallback_used=true")
        if result.reason is None:
            errors.append("degraded status requires non-empty reason")

    if result.status == "ok":
        if result.fallback_used:
            errors.append("ok status must not use fallback")
        if result.reason is not None:
            errors.append("ok status must not contain reason")

    if result.status == "error" and result.fallback_used:
        errors.append("error status must not use fallback")

    if result.reason == "provider_unavailable":
        if result.status != "degraded":
            errors.append("provider_unavailable reason requires degraded status")
        if not result.fallback_used:
            errors.append("provider_unavailable reason requires fallback_used=true")

    return errors
