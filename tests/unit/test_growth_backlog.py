from __future__ import annotations

from pathlib import Path

import pytest

from lam_test_agent_growth_data import collect_growth_snapshot, write_snapshot
from lam_test_agent_growth_backlog import (
    generate_backlog_items,
    load_snapshot,
    main as growth_backlog_main,
    render_backlog_markdown,
)


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.unit
def test_generate_backlog_items_respects_limits(tmp_path: Path) -> None:
    snap = collect_growth_snapshot(ROOT)
    path = tmp_path / "snapshot.json"
    write_snapshot(snap, path)
    loaded = load_snapshot(path)
    items = generate_backlog_items(loaded, max_total=5, max_per_route=1)
    assert len(items) <= 5
    per_route: dict[str, int] = {}
    for item in items:
        per_route[item.route_id] = per_route.get(item.route_id, 0) + 1
    assert all(v <= 1 for v in per_route.values())


@pytest.mark.unit
def test_render_backlog_markdown_contains_safety_guardrails(tmp_path: Path) -> None:
    snap = collect_growth_snapshot(ROOT)
    path = tmp_path / "snapshot.json"
    write_snapshot(snap, path)
    loaded = load_snapshot(path)
    items = generate_backlog_items(loaded, max_total=3, max_per_route=1)
    text = render_backlog_markdown(items, loaded)
    assert "## Safety Guardrails" in text
    assert "No recursive self-expansion" in text


@pytest.mark.unit
def test_load_snapshot_rejects_invalid_shape(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text('{"routes": "not-a-list"}', encoding="utf-8")
    with pytest.raises(ValueError, match="snapshot.routes must be list"):
        load_snapshot(bad)


@pytest.mark.unit
def test_generate_backlog_items_rejects_invalid_limits(tmp_path: Path) -> None:
    snap = collect_growth_snapshot(ROOT)
    path = tmp_path / "snapshot.json"
    write_snapshot(snap, path)
    loaded = load_snapshot(path)
    with pytest.raises(ValueError, match="max_total and max_per_route must be > 0"):
        generate_backlog_items(loaded, max_total=0, max_per_route=1)


@pytest.mark.unit
def test_load_snapshot_rejects_too_large_routes(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text('{"routes": [%s]}' % ",".join(["{}"] * 201), encoding="utf-8")
    with pytest.raises(ValueError, match="snapshot.routes too large"):
        load_snapshot(bad)


@pytest.mark.unit
def test_growth_backlog_main_returns_2_on_invalid_snapshot_json(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("not-json", encoding="utf-8")
    rc = growth_backlog_main(
        [
            "--snapshot",
            str(bad),
            "--output",
            str(tmp_path / "out.md"),
        ]
    )
    assert rc == 2
