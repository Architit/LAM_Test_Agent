from __future__ import annotations

from pathlib import Path

import pytest

from lam_test_agent_plan_guard import (
    detect_adjacent_duplicates,
    detect_repeating_cycles,
    ecosystem_markdown_files,
    extract_execution_events,
    validate_many,
    validate_plan_file,
)


@pytest.mark.unit
def test_extract_execution_events_parses_log_lines() -> None:
    text = """
- 2026-02-17: First event
- 2026-02-17: Second event
"""
    assert extract_execution_events(text) == ["First event", "Second event"]


@pytest.mark.unit
def test_extract_execution_events_parses_plain_timestamp_lines() -> None:
    text = """
2026-02-17 00:43 UTC — Deep analysis completed
2026-02-17 00:51 UTC — Stabilization implemented
"""
    assert extract_execution_events(text) == ["Deep analysis completed", "Stabilization implemented"]


@pytest.mark.unit
def test_detect_adjacent_duplicates_finds_duplicate() -> None:
    events = ["a", "a", "b"]
    errors = detect_adjacent_duplicates(events)
    assert len(errors) == 1


@pytest.mark.unit
def test_detect_repeating_cycles_finds_tail_pattern() -> None:
    events = ["x", "y", "x", "y", "x", "y"]
    out = detect_repeating_cycles(events, max_window=3, min_repeats=3, tail_only=True)
    assert out


@pytest.mark.unit
def test_detect_repeating_cycles_finds_global_pattern_not_only_tail() -> None:
    events = ["start", "a", "b", "a", "b", "a", "b", "end"]
    out = detect_repeating_cycles(events, max_window=3, min_repeats=3, tail_only=False)
    assert any("window=2" in x for x in out)


@pytest.mark.unit
def test_detect_repeating_cycles_handles_single_event_loops() -> None:
    events = ["a", "a", "a", "x"]
    out = detect_repeating_cycles(events, max_window=2, min_repeats=3, tail_only=False)
    assert any("window=1" in x for x in out)


@pytest.mark.unit
def test_validate_plan_file_ok_for_current_front_plan() -> None:
    root = Path(__file__).resolve().parents[2]
    plan = root / "memory" / "FRONT" / "TEST_MATRIX_EXPANSION_EXEC_PLAN_2026-02-17.md"
    assert validate_plan_file(plan) == []


@pytest.mark.unit
def test_ecosystem_markdown_files_collects_memory_and_root(tmp_path: Path) -> None:
    (tmp_path / "memory" / "FRONT").mkdir(parents=True)
    (tmp_path / "memory" / "FRONT" / "a.md").write_text("x", encoding="utf-8")
    (tmp_path / "ROOT.md").write_text("x", encoding="utf-8")
    files = ecosystem_markdown_files(tmp_path)
    names = {p.name for p in files}
    assert "a.md" in names and "ROOT.md" in names


@pytest.mark.unit
def test_validate_many_reports_file_prefixed_errors(tmp_path: Path) -> None:
    bad = tmp_path / "bad.md"
    bad.write_text(
        "\n".join(
            [
                "- 2026-02-17: A",
                "- 2026-02-17: B",
                "- 2026-02-17: A",
                "- 2026-02-17: B",
                "- 2026-02-17: A",
                "- 2026-02-17: B",
            ]
        ),
        encoding="utf-8",
    )
    errors = validate_many([bad])
    assert errors
    assert str(bad) in errors[0]
