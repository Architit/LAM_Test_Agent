from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"json must be object: {path}")
    return data


def parse_utc(ts: str) -> datetime:
    if not isinstance(ts, str) or not ts.strip():
        raise ValueError("timestamp must be non-empty string")
    normalized = ts.strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return dt.astimezone(timezone.utc)


def validate_freshness_and_order(
    *,
    growth_snapshot: dict[str, Any],
    before_after: dict[str, Any],
    live_policy: dict[str, Any],
    phase_drift: dict[str, Any],
    ttl_hours: int,
    now_utc: datetime,
) -> list[str]:
    errors: list[str] = []

    growth_ts = parse_utc(str(growth_snapshot.get("generated_at_utc", "")))
    before_after_ts = parse_utc(str(before_after.get("generated_at_utc", "")))
    before_after_after_ts = parse_utc(
        str(before_after.get("after", {}).get("observed_snapshot_generated_at_utc", ""))
    )
    live_policy_ts = parse_utc(str(live_policy.get("generated_at_utc", "")))
    phase_drift_ts = parse_utc(str(phase_drift.get("generated_at_utc", "")))

    ttl_seconds = ttl_hours * 3600
    named = [
        ("growth_snapshot", growth_ts),
        ("before_after", before_after_ts),
        ("before_after.after_snapshot", before_after_after_ts),
        ("live_policy", live_policy_ts),
        ("phase_drift", phase_drift_ts),
    ]

    for name, ts in named:
        age = (now_utc - ts).total_seconds()
        if age < 0:
            errors.append(f"{name} timestamp is in the future")
        elif age > ttl_seconds:
            errors.append(f"{name} is stale: age_seconds={int(age)} ttl_seconds={ttl_seconds}")

    if before_after_after_ts != growth_ts:
        errors.append("before_after.after.observed_snapshot_generated_at_utc must match growth_snapshot.generated_at_utc")
    if before_after_ts < growth_ts:
        errors.append("before_after.generated_at_utc must be >= growth_snapshot.generated_at_utc")
    if live_policy_ts < growth_ts:
        errors.append("live_policy.generated_at_utc must be >= growth_snapshot.generated_at_utc")
    if phase_drift_ts < live_policy_ts:
        errors.append("phase_drift.generated_at_utc must be >= live_policy.generated_at_utc")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate telemetry freshness and timestamp chain.")
    parser.add_argument("--ttl-hours", type=int, default=12)
    parser.add_argument("--growth", default="memory/FRONT/TEST_MATRIX_GROWTH_SNAPSHOT.json")
    parser.add_argument("--before-after", default="memory/FRONT/TEST_MATRIX_GROWTH_BEFORE_AFTER.json")
    parser.add_argument("--live-policy", default="memory/FRONT/LIVE_ACTIVATION_POLICY_REPORT.json")
    parser.add_argument("--phase-drift", default="memory/FRONT/PHASE_E_DRIFT_REPORT.json")
    parser.add_argument("--now-utc", default="")
    args = parser.parse_args(argv)

    paths = {
        "growth": Path(args.growth).resolve(),
        "before_after": Path(args.before_after).resolve(),
        "live_policy": Path(args.live_policy).resolve(),
        "phase_drift": Path(args.phase_drift).resolve(),
    }
    for name, path in paths.items():
        if not path.exists():
            print(f"TELEMETRY_FRESHNESS_GATE_FAIL missing_{name}={path}")
            return 2

    try:
        now_utc = parse_utc(args.now_utc) if args.now_utc else datetime.now(timezone.utc)
        errors = validate_freshness_and_order(
            growth_snapshot=load_json(paths["growth"]),
            before_after=load_json(paths["before_after"]),
            live_policy=load_json(paths["live_policy"]),
            phase_drift=load_json(paths["phase_drift"]),
            ttl_hours=args.ttl_hours,
            now_utc=now_utc,
        )
    except Exception as exc:  # pragma: no cover
        print(f"TELEMETRY_FRESHNESS_GATE_FAIL error={exc}")
        return 2

    if errors:
        for err in errors:
            print(f"TELEMETRY_FRESHNESS_GATE_FAIL {err}")
        return 1

    print(
        "TELEMETRY_FRESHNESS_GATE_OK "
        f"ttl_hours={args.ttl_hours} now_utc={now_utc.isoformat()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
