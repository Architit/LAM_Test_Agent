from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ScenarioRoute:
    source: str
    target: str
    layer: str


@dataclass(frozen=True)
class ScenarioSpec:
    scenario_id: str
    title: str
    routes: tuple[ScenarioRoute, ...]
    required_contracts: tuple[str, ...]
    expected_status: str


def load_scenarios(root: Path) -> list[ScenarioSpec]:
    scenarios_dir = root / "tests" / "scenarios"
    specs: list[ScenarioSpec] = []
    if not scenarios_dir.exists():
        return specs
    for p in sorted(scenarios_dir.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{p.name}: invalid JSON: {exc.msg}") from exc

        if not isinstance(data, dict):
            raise ValueError(f"{p.name}: top-level JSON must be object")

        errors = validate_scenario_dict(data)
        if errors:
            raise ValueError(f"{p.name}: invalid scenario schema: {'; '.join(errors)}")

        routes = tuple(
            ScenarioRoute(
                source=str(r["source"]),
                target=str(r["target"]),
                layer=str(r["layer"]),
            )
            for r in data.get("routes", [])
        )
        specs.append(
            ScenarioSpec(
                scenario_id=str(data["scenario_id"]),
                title=str(data["title"]),
                routes=routes,
                required_contracts=tuple(str(x) for x in data.get("required_contracts", [])),
                expected_status=str(data.get("expected_status", "ok")),
            )
        )
    return specs


def validate_scenario_dict(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in ("scenario_id", "title", "routes", "required_contracts", "expected_status"):
        if field not in data:
            errors.append(f"missing field: {field}")
    if "scenario_id" in data and (not isinstance(data["scenario_id"], str) or not data["scenario_id"].strip()):
        errors.append("scenario_id must be non-empty string")
    if "title" in data and (not isinstance(data["title"], str) or not data["title"].strip()):
        errors.append("title must be non-empty string")
    if "routes" in data:
        routes = data["routes"]
        if not isinstance(routes, list) or len(routes) == 0:
            errors.append("routes must be non-empty list")
        else:
            for i, route in enumerate(routes):
                if not isinstance(route, dict):
                    errors.append(f"route[{i}] must be dict")
                    continue
                for key in ("source", "target", "layer"):
                    if key not in route:
                        errors.append(f"route[{i}] missing {key}")
                    elif not isinstance(route[key], str) or not route[key].strip():
                        errors.append(f"route[{i}] {key} must be non-empty string")
    if "required_contracts" in data:
        rc = data["required_contracts"]
        if not isinstance(rc, list) or len(rc) == 0:
            errors.append("required_contracts must be non-empty list")
        elif not all(isinstance(x, str) and x.strip() for x in rc):
            errors.append("required_contracts items must be non-empty strings")
    if "expected_status" in data and data["expected_status"] not in {"ok", "error", "degraded"}:
        errors.append("expected_status must be one of: ok,error,degraded")
    return errors
