from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MAX_ROUTE_ROWS = 200
DEFAULT_MAX_TOTAL = 24
DEFAULT_MAX_PER_ROUTE = 3


@dataclass(frozen=True)
class BacklogItem:
    priority: str
    route_id: str
    scenario_id: str
    title: str
    acceptance: str


def _sort_key(route: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(route.get("priority", "P9")),
        str(route.get("route_id", "")),
        str(route.get("scenario_id", "")),
        str(route.get("source", "")),
        str(route.get("target", "")),
    )


def _task_templates(route: dict[str, Any]) -> list[BacklogItem]:
    route_id = str(route["route_id"])
    scenario_id = str(route["scenario_id"])
    priority = str(route.get("priority", "P1"))
    gaps = set(str(x) for x in route.get("gap_tags", []))
    source = str(route.get("source", "unknown"))
    target = str(route.get("target", "unknown"))

    tasks: list[BacklogItem] = []
    if "live_execution_missing" in gaps:
        tasks.append(
            BacklogItem(
                priority=priority,
                route_id=route_id,
                scenario_id=scenario_id,
                title=f"Enable live route test for {route_id} ({source} -> {target})",
                acceptance="Live mode executes scenario route with real submodule agents and preserves trace continuity.",
            )
        )
    if "contract_assertions_missing" in gaps:
        tasks.append(
            BacklogItem(
                priority=priority,
                route_id=route_id,
                scenario_id=scenario_id,
                title=f"Add contract assertions for {route_id}",
                acceptance="Route test asserts envelope schema, status semantics, and trace_id format.",
            )
        )
    if "failure_assertions_missing" in gaps:
        tasks.append(
            BacklogItem(
                priority=priority,
                route_id=route_id,
                scenario_id=scenario_id,
                title=f"Add failure-topology assertions for {route_id}",
                acceptance="Route test asserts degraded/error behavior under outage and malformed payloads.",
            )
        )
    if "mock_execution_missing" in gaps:
        tasks.append(
            BacklogItem(
                priority=priority,
                route_id=route_id,
                scenario_id=scenario_id,
                title=f"Add deterministic mock execution for {route_id}",
                acceptance="Mock route execution exists and is validated by integration tests.",
            )
        )
    return tasks


def load_snapshot(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("snapshot must be JSON object")
    routes = data.get("routes")
    if not isinstance(routes, list):
        raise ValueError("snapshot.routes must be list")
    if len(routes) > MAX_ROUTE_ROWS:
        raise ValueError(f"snapshot.routes too large: {len(routes)} > {MAX_ROUTE_ROWS}")
    return data


def generate_backlog_items(
    snapshot: dict[str, Any],
    *,
    max_total: int = DEFAULT_MAX_TOTAL,
    max_per_route: int = DEFAULT_MAX_PER_ROUTE,
) -> list[BacklogItem]:
    if max_total <= 0 or max_per_route <= 0:
        raise ValueError("max_total and max_per_route must be > 0")

    routes = snapshot.get("routes", [])
    if not isinstance(routes, list):
        raise ValueError("snapshot.routes must be list")

    items: list[BacklogItem] = []
    per_route_counter: dict[str, int] = {}

    for route in sorted(routes, key=_sort_key):
        if not isinstance(route, dict):
            continue
        route_id = str(route.get("route_id", "unknown"))
        current = per_route_counter.get(route_id, 0)
        remaining = max_per_route - current
        if remaining <= 0:
            continue
        for task in _task_templates(route)[:remaining]:
            if len(items) >= max_total:
                return items
            items.append(task)
            per_route_counter[route_id] = per_route_counter.get(route_id, 0) + 1
    return items


def render_backlog_markdown(items: list[BacklogItem], snapshot: dict[str, Any]) -> str:
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# TEST_MATRIX_GROWTH_BACKLOG",
        "",
        f"Generated: {generated}",
        "",
        "## Safety Guardrails",
        "- Deterministic generation order only.",
        "- Hard caps active: max tasks and per-route limit.",
        "- No recursive self-expansion; generator outputs one backlog artifact only.",
        "",
        "## Snapshot Summary",
        f"- routes_total: {snapshot.get('summary', {}).get('routes_total', 'n/a')}",
        f"- unique_route_ids: {snapshot.get('summary', {}).get('unique_route_ids', 'n/a')}",
        f"- live_ready: {snapshot.get('summary', {}).get('live_ready', 'n/a')}",
        "",
        "## Backlog Items",
    ]
    if not items:
        lines.append("- No backlog items generated from current snapshot gaps.")
        return "\n".join(lines) + "\n"

    for item in items:
        lines.append(f"- [{item.priority}] {item.route_id} / {item.scenario_id}: {item.title}")
        lines.append(f"  Acceptance: {item.acceptance}")
    return "\n".join(lines) + "\n"


def write_backlog(text: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate bounded growth backlog from snapshot.")
    parser.add_argument("--snapshot", default="memory/FRONT/TEST_MATRIX_GROWTH_SNAPSHOT.json")
    parser.add_argument("--output", default="memory/FRONT/TEST_MATRIX_GROWTH_BACKLOG.md")
    parser.add_argument("--max-total", type=int, default=DEFAULT_MAX_TOTAL)
    parser.add_argument("--max-per-route", type=int, default=DEFAULT_MAX_PER_ROUTE)
    args = parser.parse_args(argv)

    snapshot_path = Path(args.snapshot).resolve()
    if not snapshot_path.exists():
        print(f"snapshot not found: {snapshot_path}")
        return 2

    snapshot = load_snapshot(snapshot_path)
    items = generate_backlog_items(snapshot, max_total=args.max_total, max_per_route=args.max_per_route)
    text = render_backlog_markdown(items, snapshot)

    output = Path(args.output).resolve()
    write_backlog(text, output)
    print(f"GROWTH_BACKLOG_OK items={len(items)} output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
