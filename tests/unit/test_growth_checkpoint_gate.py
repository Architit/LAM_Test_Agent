from __future__ import annotations

import json
from pathlib import Path

import pytest

from lam_test_agent_growth_checkpoint_gate import validate_checkpoint, validate_checkpoint_snapshot_sync


def _valid_payload() -> dict[str, dict[str, object]]:
    return {
        "before": {
            "deadloop_cross_repo_block_present": False,
            "per_route_deadloop_assertion_field_present": False,
        },
        "after": {
            "observed_snapshot_generated_at_utc": "2026-02-17T22:22:18.093527+00:00",
            "deadloop_cross_repo": {
                "has_cross_repo_assertions": True,
                "guard_script_present": True,
                "ecosystem_scan_script_present": True,
                "cross_repo_ready": True,
            },
            "per_route_deadloop_assertion_field_present": True,
        },
        "delta": {
            "new_summary_blocks": ["deadloop_cross_repo"],
            "new_per_route_fields": ["has_deadloop_cross_repo_assertions"],
        },
    }


def _valid_snapshot() -> dict[str, object]:
    return {
        "generated_at_utc": "2026-02-17T22:22:18.093527+00:00",
        "summary": {
            "deadloop_cross_repo": {
                "has_cross_repo_assertions": True,
                "guard_script_present": True,
                "ecosystem_scan_script_present": True,
                "cross_repo_ready": True,
            }
        },
        "routes": [
            {"has_deadloop_cross_repo_assertions": True},
            {"has_deadloop_cross_repo_assertions": True},
        ],
    }


@pytest.mark.unit
def test_validate_checkpoint_accepts_valid_payload() -> None:
    errors = validate_checkpoint(_valid_payload(), "## Before\n\n## After\n\n## Delta\n")
    assert errors == []


@pytest.mark.unit
def test_validate_checkpoint_rejects_missing_deadloop_block() -> None:
    payload = _valid_payload()
    del payload["after"]["deadloop_cross_repo"]  # type: ignore[index]
    errors = validate_checkpoint(payload, "## Before\n\n## After\n\n## Delta\n")
    assert any("after.deadloop_cross_repo must be object" in e for e in errors)


@pytest.mark.unit
def test_validate_checkpoint_rejects_missing_markdown_sections() -> None:
    errors = validate_checkpoint(_valid_payload(), "# no sections\n")
    assert any("markdown checkpoint must include" in e for e in errors)


@pytest.mark.unit
def test_validate_checkpoint_serialized_shape_roundtrip(tmp_path: Path) -> None:
    payload = _valid_payload()
    p = tmp_path / "checkpoint.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    loaded = json.loads(p.read_text(encoding="utf-8"))
    errors = validate_checkpoint(loaded, "## Before\n\n## After\n\n## Delta\n")
    assert errors == []


@pytest.mark.unit
def test_validate_checkpoint_snapshot_sync_accepts_matching_data() -> None:
    errors = validate_checkpoint_snapshot_sync(_valid_payload(), _valid_snapshot())
    assert errors == []


@pytest.mark.unit
def test_validate_checkpoint_snapshot_sync_rejects_timestamp_mismatch() -> None:
    checkpoint = _valid_payload()
    snapshot = _valid_snapshot()
    snapshot["generated_at_utc"] = "2026-02-17T22:25:00+00:00"
    errors = validate_checkpoint_snapshot_sync(checkpoint, snapshot)
    assert any("timestamp must match" in e for e in errors)
