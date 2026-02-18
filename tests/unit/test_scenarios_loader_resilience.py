from __future__ import annotations

from pathlib import Path

import pytest

from lam_test_agent_scenarios import load_scenarios


@pytest.mark.unit
def test_load_scenarios_raises_on_invalid_json(tmp_path: Path) -> None:
    scenarios_dir = tmp_path / "tests" / "scenarios"
    scenarios_dir.mkdir(parents=True)
    (scenarios_dir / "bad.json").write_text("{bad", encoding="utf-8")

    with pytest.raises(ValueError, match=r"bad\.json: invalid JSON"):
        load_scenarios(tmp_path)


@pytest.mark.unit
def test_load_scenarios_raises_on_invalid_schema(tmp_path: Path) -> None:
    scenarios_dir = tmp_path / "tests" / "scenarios"
    scenarios_dir.mkdir(parents=True)
    (scenarios_dir / "bad_schema.json").write_text(
        '{"scenario_id":"x","title":"t","routes":[],"required_contracts":[],"expected_status":"ok"}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"bad_schema\.json: invalid scenario schema:"):
        load_scenarios(tmp_path)
