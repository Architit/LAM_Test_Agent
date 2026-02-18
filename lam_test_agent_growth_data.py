from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lam_test_agent_bootstrap import missing_agent_src_paths
from lam_test_agent_paths import lam_root
from lam_test_agent_route_matrix import SCENARIO_ROUTE_IDS
from lam_test_agent_scenarios import load_scenarios


@dataclass(frozen=True)
class RouteGrowthRow:
    route_id: str
    scenario_id: str
    source: str
    target: str
    layer: str
    expected_status: str
    required_contracts: tuple[str, ...]
    has_mock_execution: bool
    has_contract_assertions: bool
    has_failure_assertions: bool
    has_deadloop_cross_repo_assertions: bool
    live_ready: bool
    live_executed: bool
    gap_tags: tuple[str, ...]
    priority: str


def _priority_for_gaps(gaps: tuple[str, ...]) -> str:
    if "live_execution_missing" in gaps:
        return "P0"
    if "contract_assertions_missing" in gaps or "failure_assertions_missing" in gaps:
        return "P1"
    if "mock_execution_missing" in gaps:
        return "P1"
    return "P2"


def collect_growth_snapshot(root: Path) -> dict[str, Any]:
    specs = load_scenarios(root)
    spec_by_id = {s.scenario_id: s for s in specs}
    mapped_scenario_ids = set(SCENARIO_ROUTE_IDS)
    loaded_scenario_ids = set(spec_by_id)

    unmapped_specs = sorted(loaded_scenario_ids - mapped_scenario_ids)
    if unmapped_specs:
        raise ValueError(
            "scenarios missing route-id mapping: " + ", ".join(unmapped_specs)
        )

    missing_specs = sorted(mapped_scenario_ids - loaded_scenario_ids)
    if missing_specs:
        raise ValueError(
            "route-id mapping has no scenario spec: " + ", ".join(missing_specs)
        )

    missing_paths = tuple(str(p) for p in missing_agent_src_paths(root))
    live_ready = len(missing_paths) == 0

    has_mock_execution = (root / "tests" / "it" / "test_route_matrix_mock.py").exists()
    has_contract_assertions = (root / "tests" / "it" / "test_route_matrix_contracts.py").exists()
    has_failure_assertions = (root / "tests" / "it" / "test_route_matrix_failure_topology.py").exists()
    has_deadloop_cross_repo_assertions = (root / "tests" / "it" / "test_deadloop_cross_repo.py").exists()

    ecosystem_lam_root = lam_root()
    deadloop_guard_script_exists = (ecosystem_lam_root / "scripts" / "deadloop_guard_entrypoint.py").exists()
    deadloop_scan_script_exists = (ecosystem_lam_root / "scripts" / "deadloop_ecosystem_scan.py").exists()
    deadloop_cross_repo_ready = deadloop_guard_script_exists and deadloop_scan_script_exists

    rows: list[RouteGrowthRow] = []
    for scenario_id, route_ids in SCENARIO_ROUTE_IDS.items():
        spec = spec_by_id.get(scenario_id)
        if spec is None:
            raise ValueError(f"scenario spec not found for mapping: {scenario_id}")
        if len(route_ids) != len(spec.routes):
            raise ValueError(
                f"route count mismatch for {scenario_id}: "
                f"{len(route_ids)} route ids for {len(spec.routes)} scenario routes"
            )
        for route_id, route in zip(route_ids, spec.routes, strict=True):
            gaps: list[str] = []
            if not has_mock_execution:
                gaps.append("mock_execution_missing")
            if not has_contract_assertions:
                gaps.append("contract_assertions_missing")
            if not has_failure_assertions:
                gaps.append("failure_assertions_missing")
            if not live_ready:
                gaps.append("live_execution_missing")

            gap_tags = tuple(gaps)
            rows.append(
                RouteGrowthRow(
                    route_id=route_id,
                    scenario_id=scenario_id,
                    source=route.source,
                    target=route.target,
                    layer=route.layer,
                    expected_status=spec.expected_status,
                    required_contracts=spec.required_contracts,
                    has_mock_execution=has_mock_execution,
                    has_contract_assertions=has_contract_assertions,
                    has_failure_assertions=has_failure_assertions,
                    has_deadloop_cross_repo_assertions=has_deadloop_cross_repo_assertions,
                    live_ready=live_ready,
                    live_executed=False,
                    gap_tags=gap_tags,
                    priority=_priority_for_gaps(gap_tags),
                )
            )

    priorities = {r.priority for r in rows}
    summary = {
        "routes_total": len(rows),
        "unique_route_ids": len({r.route_id for r in rows}),
        "live_ready": live_ready,
        "deadloop_cross_repo": {
            "has_cross_repo_assertions": has_deadloop_cross_repo_assertions,
            "guard_script_present": deadloop_guard_script_exists,
            "ecosystem_scan_script_present": deadloop_scan_script_exists,
            "cross_repo_ready": deadloop_cross_repo_ready,
        },
        "priority_counts": {
            "P0": sum(1 for r in rows if r.priority == "P0"),
            "P1": sum(1 for r in rows if r.priority == "P1"),
            "P2": sum(1 for r in rows if r.priority == "P2"),
        },
        "priorities_present": sorted(priorities),
    }

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository_root": str(root),
        "missing_submodule_paths": list(missing_paths),
        "summary": summary,
        "routes": [
            {
                **asdict(r),
                "required_contracts": list(r.required_contracts),
                "gap_tags": list(r.gap_tags),
            }
            for r in rows
        ],
    }


def write_snapshot(snapshot: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect growth data snapshot for route-matrix test expansion.")
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument("--output", default="memory/FRONT/TEST_MATRIX_GROWTH_SNAPSHOT.json", help="Output JSON file.")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    try:
        snapshot = collect_growth_snapshot(root)
        output = root / args.output
        write_snapshot(snapshot, output)
    except Exception as exc:
        print(f"GROWTH_SNAPSHOT_FAIL error={type(exc).__name__}: {exc}")
        return 2
    print(f"GROWTH_SNAPSHOT_OK routes={snapshot['summary']['routes_total']} output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
