from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _is_bool(value: Any) -> bool:
    return isinstance(value, bool)


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("checkpoint json must be object")
    return data


def validate_checkpoint(data: dict[str, Any], markdown_text: str) -> list[str]:
    errors: list[str] = []

    for key in ("before", "after", "delta"):
        if key not in data or not isinstance(data[key], dict):
            errors.append(f"missing object: {key}")

    before = data.get("before", {})
    after = data.get("after", {})
    delta = data.get("delta", {})

    if before:
        if not _is_bool(before.get("deadloop_cross_repo_block_present")):
            errors.append("before.deadloop_cross_repo_block_present must be bool")
        if not _is_bool(before.get("per_route_deadloop_assertion_field_present")):
            errors.append("before.per_route_deadloop_assertion_field_present must be bool")

    if after:
        dcr = after.get("deadloop_cross_repo")
        if not isinstance(dcr, dict):
            errors.append("after.deadloop_cross_repo must be object")
        else:
            required_true = (
                "has_cross_repo_assertions",
                "guard_script_present",
                "ecosystem_scan_script_present",
                "cross_repo_ready",
            )
            for key in required_true:
                if dcr.get(key) is not True:
                    errors.append(f"after.deadloop_cross_repo.{key} must be true")
        if after.get("per_route_deadloop_assertion_field_present") is not True:
            errors.append("after.per_route_deadloop_assertion_field_present must be true")

    if delta:
        new_blocks = delta.get("new_summary_blocks")
        new_fields = delta.get("new_per_route_fields")
        if not isinstance(new_blocks, list) or "deadloop_cross_repo" not in new_blocks:
            errors.append("delta.new_summary_blocks must contain deadloop_cross_repo")
        if not isinstance(new_fields, list) or "has_deadloop_cross_repo_assertions" not in new_fields:
            errors.append("delta.new_per_route_fields must contain has_deadloop_cross_repo_assertions")

    if "## Before" not in markdown_text or "## After" not in markdown_text or "## Delta" not in markdown_text:
        errors.append("markdown checkpoint must include ## Before / ## After / ## Delta sections")

    return errors


def validate_checkpoint_snapshot_sync(checkpoint: dict[str, Any], snapshot: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    cp_after = checkpoint.get("after", {})
    if not isinstance(cp_after, dict):
        return ["checkpoint.after must be object for snapshot sync"]

    cp_snapshot_ts = cp_after.get("observed_snapshot_generated_at_utc")
    snap_ts = snapshot.get("generated_at_utc")
    if not isinstance(cp_snapshot_ts, str) or not cp_snapshot_ts.strip():
        errors.append("after.observed_snapshot_generated_at_utc must be non-empty string")
    if not isinstance(snap_ts, str) or not snap_ts.strip():
        errors.append("snapshot.generated_at_utc must be non-empty string")
    if isinstance(cp_snapshot_ts, str) and isinstance(snap_ts, str) and cp_snapshot_ts != snap_ts:
        errors.append("checkpoint after timestamp must match snapshot generated_at_utc")

    snap_summary = snapshot.get("summary", {})
    if not isinstance(snap_summary, dict):
        errors.append("snapshot.summary must be object")
        return errors

    snap_dcr = snap_summary.get("deadloop_cross_repo")
    cp_dcr = cp_after.get("deadloop_cross_repo")
    if not isinstance(snap_dcr, dict):
        errors.append("snapshot.summary.deadloop_cross_repo must be object")
    if not isinstance(cp_dcr, dict):
        errors.append("checkpoint.after.deadloop_cross_repo must be object")
    if isinstance(snap_dcr, dict) and isinstance(cp_dcr, dict) and snap_dcr != cp_dcr:
        errors.append("checkpoint.after.deadloop_cross_repo must match snapshot.summary.deadloop_cross_repo")

    routes = snapshot.get("routes", [])
    if not isinstance(routes, list):
        errors.append("snapshot.routes must be list")
    else:
        missing = 0
        false_count = 0
        for row in routes:
            if not isinstance(row, dict):
                continue
            if "has_deadloop_cross_repo_assertions" not in row:
                missing += 1
            elif row["has_deadloop_cross_repo_assertions"] is not True:
                false_count += 1
        if missing > 0:
            errors.append("snapshot.routes missing has_deadloop_cross_repo_assertions field")
        if false_count > 0:
            errors.append("snapshot.routes has_deadloop_cross_repo_assertions must be true for all routes")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate growth before/after checkpoint artifact.")
    parser.add_argument(
        "--json",
        default="memory/FRONT/TEST_MATRIX_GROWTH_BEFORE_AFTER.json",
        help="Path to before/after checkpoint JSON",
    )
    parser.add_argument(
        "--md",
        default="memory/FRONT/TEST_MATRIX_GROWTH_BEFORE_AFTER.md",
        help="Path to before/after checkpoint Markdown",
    )
    parser.add_argument(
        "--snapshot",
        default="memory/FRONT/TEST_MATRIX_GROWTH_SNAPSHOT.json",
        help="Path to growth snapshot JSON for sync validation",
    )
    args = parser.parse_args(argv)

    json_path = Path(args.json).resolve()
    md_path = Path(args.md).resolve()
    snapshot_path = Path(args.snapshot).resolve()
    if not json_path.exists():
        print(f"GROWTH_CHECKPOINT_GATE_FAIL missing_json={json_path}")
        return 2
    if not md_path.exists():
        print(f"GROWTH_CHECKPOINT_GATE_FAIL missing_md={md_path}")
        return 2
    if not snapshot_path.exists():
        print(f"GROWTH_CHECKPOINT_GATE_FAIL missing_snapshot={snapshot_path}")
        return 2

    try:
        checkpoint = load_json(json_path)
        snapshot = load_json(snapshot_path)
        md_text = md_path.read_text(encoding="utf-8")
        errors = validate_checkpoint(checkpoint, md_text)
        errors.extend(validate_checkpoint_snapshot_sync(checkpoint, snapshot))
    except Exception as exc:  # pragma: no cover
        print(f"GROWTH_CHECKPOINT_GATE_FAIL error={exc}")
        return 2

    if errors:
        for err in errors:
            print(f"GROWTH_CHECKPOINT_GATE_FAIL {err}")
        return 1

    print(f"GROWTH_CHECKPOINT_GATE_OK json={json_path} md={md_path} snapshot={snapshot_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
