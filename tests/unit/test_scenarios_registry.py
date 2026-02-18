from __future__ import annotations

import json
from pathlib import Path

import pytest

from lam_test_agent_scenarios import load_scenarios, validate_scenario_dict


ROOT = Path(__file__).resolve().parents[2]
SCENARIOS_DIR = ROOT / "tests" / "scenarios"


@pytest.mark.unit
def test_scenarios_directory_exists() -> None:
    assert SCENARIOS_DIR.exists() and SCENARIOS_DIR.is_dir()


@pytest.mark.unit
def test_at_least_three_route_scenarios_present() -> None:
    files = sorted(SCENARIOS_DIR.glob("*.json"))
    assert len(files) >= 3


@pytest.mark.unit
def test_load_scenarios_returns_non_empty_specs() -> None:
    specs = load_scenarios(ROOT)
    assert len(specs) >= 3
    assert all(spec.scenario_id for spec in specs)


@pytest.mark.unit
def test_scenario_ids_are_unique() -> None:
    specs = load_scenarios(ROOT)
    ids = [s.scenario_id for s in specs]
    assert len(ids) == len(set(ids))


@pytest.mark.unit
def test_scenarios_have_routes_and_contracts() -> None:
    specs = load_scenarios(ROOT)
    for spec in specs:
        assert len(spec.routes) > 0
        assert len(spec.required_contracts) > 0


@pytest.mark.unit
@pytest.mark.parametrize(
    "filename",
    [
        "codex_comm_ping_pong.json",
        "comm_roaudter_fallback.json",
        "taskarid_chain_route.json",
    ],
)
def test_validate_real_scenario_files(filename: str) -> None:
    data = json.loads((SCENARIOS_DIR / filename).read_text(encoding="utf-8"))
    assert validate_scenario_dict(data) == []


@pytest.mark.unit
@pytest.mark.parametrize(
    "payload,expected",
    [
        ({}, "missing field: scenario_id"),
        ({"scenario_id": "", "title": "x", "routes": [], "required_contracts": [], "expected_status": "ok"}, "scenario_id must be non-empty string"),
        ({"scenario_id": "x", "title": "", "routes": [], "required_contracts": [], "expected_status": "ok"}, "title must be non-empty string"),
        ({"scenario_id": "x", "title": "t", "routes": [], "required_contracts": ["a"], "expected_status": "ok"}, "routes must be non-empty list"),
        ({"scenario_id": "x", "title": "t", "routes": [{}], "required_contracts": ["a"], "expected_status": "ok"}, "route[0] missing source"),
        ({"scenario_id": "x", "title": "t", "routes": [{"source": "a", "target": "b", "layer": "c"}], "required_contracts": [], "expected_status": "ok"}, "required_contracts must be non-empty list"),
        ({"scenario_id": "x", "title": "t", "routes": [{"source": "a", "target": "b", "layer": "c"}], "required_contracts": ["a"], "expected_status": "bad"}, "expected_status must be one of: ok,error,degraded"),
    ],
)
def test_validate_scenario_dict_negative(payload: dict, expected: str) -> None:
    errors = validate_scenario_dict(payload)
    assert expected in errors
