from __future__ import annotations

import json
from pathlib import Path

import pytest

import lam_test_agent_growth_data as growth_data
from lam_test_agent_growth_data import collect_growth_snapshot, write_snapshot


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.unit
def test_collect_growth_snapshot_has_expected_shape() -> None:
    snap = collect_growth_snapshot(ROOT)
    assert "summary" in snap and "routes" in snap
    assert snap["summary"]["routes_total"] == len(snap["routes"])
    assert snap["summary"]["unique_route_ids"] == 8
    assert len(snap["routes"]) >= 8


@pytest.mark.unit
def test_collect_growth_snapshot_contains_priority_and_gap_tags() -> None:
    snap = collect_growth_snapshot(ROOT)
    row = snap["routes"][0]
    assert "priority" in row
    assert "gap_tags" in row
    assert isinstance(row["gap_tags"], list)


@pytest.mark.unit
def test_collect_growth_snapshot_contains_deadloop_cross_repo_summary() -> None:
    snap = collect_growth_snapshot(ROOT)
    deadloop = snap["summary"]["deadloop_cross_repo"]
    assert isinstance(deadloop["has_cross_repo_assertions"], bool)
    assert isinstance(deadloop["guard_script_present"], bool)
    assert isinstance(deadloop["ecosystem_scan_script_present"], bool)
    assert isinstance(deadloop["cross_repo_ready"], bool)


@pytest.mark.unit
def test_write_snapshot_writes_json_file(tmp_path: Path) -> None:
    snap = collect_growth_snapshot(ROOT)
    output = tmp_path / "snap.json"
    write_snapshot(snap, output)
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["summary"]["routes_total"] == snap["summary"]["routes_total"]


@pytest.mark.unit
def test_collect_growth_snapshot_fails_when_mapping_missing_for_loaded_scenarios(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        growth_data,
        "SCENARIO_ROUTE_IDS",
        {"scn_codex_comm_ping_pong": ("R-001", "R-002")},
    )
    with pytest.raises(ValueError, match="scenarios missing route-id mapping"):
        collect_growth_snapshot(ROOT)


@pytest.mark.unit
def test_collect_growth_snapshot_fails_on_route_count_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    patched = dict(growth_data.SCENARIO_ROUTE_IDS)
    patched["scn_taskarid_chain_route"] = ("R-006",)
    monkeypatch.setattr(growth_data, "SCENARIO_ROUTE_IDS", patched)
    with pytest.raises(ValueError, match="route count mismatch"):
        collect_growth_snapshot(ROOT)
