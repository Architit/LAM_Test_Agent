from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from lam_test_agent_telemetry_freshness_gate import validate_freshness_and_order


def _build_payloads() -> tuple[dict[str, str], dict[str, Any], dict[str, str], dict[str, str]]:
    growth = {"generated_at_utc": "2026-02-17T22:22:18.093527+00:00"}
    before_after = {
        "generated_at_utc": "2026-02-17T22:23:30Z",
        "after": {"observed_snapshot_generated_at_utc": "2026-02-17T22:22:18.093527+00:00"},
    }
    policy = {"generated_at_utc": "2026-02-17T22:32:35.951275+00:00"}
    drift = {"generated_at_utc": "2026-02-17T22:32:35.955018+00:00"}
    return growth, before_after, policy, drift


@pytest.mark.unit
def test_validate_freshness_and_order_accepts_valid_chain() -> None:
    growth, before_after, policy, drift = _build_payloads()
    now = datetime(2026, 2, 17, 23, 0, tzinfo=timezone.utc)
    errors = validate_freshness_and_order(
        growth_snapshot=growth,
        before_after=before_after,
        live_policy=policy,
        phase_drift=drift,
        ttl_hours=12,
        now_utc=now,
    )
    assert errors == []


@pytest.mark.unit
def test_validate_freshness_and_order_rejects_stale_data() -> None:
    growth, before_after, policy, drift = _build_payloads()
    now = datetime(2026, 2, 19, 0, 0, tzinfo=timezone.utc)
    errors = validate_freshness_and_order(
        growth_snapshot=growth,
        before_after=before_after,
        live_policy=policy,
        phase_drift=drift,
        ttl_hours=6,
        now_utc=now,
    )
    assert any("is stale" in e for e in errors)


@pytest.mark.unit
def test_validate_freshness_and_order_rejects_broken_chain() -> None:
    growth, before_after, policy, drift = _build_payloads()
    before_after["after"] = {"observed_snapshot_generated_at_utc": "2026-02-17T22:20:00+00:00"}  # type: ignore[index]
    policy["generated_at_utc"] = "2026-02-17T22:00:00+00:00"  # type: ignore[index]
    now = datetime(2026, 2, 17, 23, 0, tzinfo=timezone.utc)
    errors = validate_freshness_and_order(
        growth_snapshot=growth,
        before_after=before_after,
        live_policy=policy,
        phase_drift=drift,
        ttl_hours=12,
        now_utc=now,
    )
    assert any("must match growth_snapshot" in e for e in errors)
    assert any("live_policy.generated_at_utc must be >=" in e for e in errors)
