from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_LAYER_IDS = {
    "change_budget",
    "no_recursive_generation",
    "deadloop_global_scan",
    "growth_snapshot_gate",
    "bounded_backlog_gate",
    "growth_checkpoint_gate",
    "growth_checkpoint_artifact_gate",
    "archivator_handoff_gate",
    "telemetry_freshness_gate",
    "telemetry_integrity_gate",
    "submodule_readiness_gate",
    "gateway_staging_only",
}

REQUIRED_DOMAINS = {
    "protocol",
    "gateway",
    "provisioning",
    "ci",
    "planning",
    "governance",
}

MIN_LAYER_COUNT = 20


def load_stack(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("stack document must be JSON object")
    if not isinstance(data.get("layers"), list):
        raise ValueError("layers must be list")
    return data


def validate_stack(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    layers = data.get("layers", [])
    if len(layers) < MIN_LAYER_COUNT:
        errors.append(f"layer count too small: {len(layers)} < {MIN_LAYER_COUNT}")

    ids: list[str] = []
    orders: list[int] = []
    domains: list[str] = []

    for i, layer in enumerate(layers):
        if not isinstance(layer, dict):
            errors.append(f"layer[{i}] must be object")
            continue
        layer_id = layer.get("id")
        order = layer.get("order")
        domain = layer.get("domain")
        required = layer.get("required")
        if not isinstance(layer_id, str) or not layer_id.strip():
            errors.append(f"layer[{i}] invalid id")
        else:
            ids.append(layer_id)
        if not isinstance(order, int):
            errors.append(f"layer[{i}] invalid order")
        else:
            orders.append(order)
        if not isinstance(domain, str) or not domain.strip():
            errors.append(f"layer[{i}] invalid domain")
        else:
            domains.append(domain)
        if not isinstance(required, bool):
            errors.append(f"layer[{i}] required must be bool")

    if len(ids) != len(set(ids)):
        errors.append("layer ids must be unique")
    if len(orders) != len(set(orders)):
        errors.append("layer order values must be unique")
    if sorted(orders) != list(range(1, len(orders) + 1)):
        errors.append("layer order must be contiguous starting at 1")

    missing_ids = REQUIRED_LAYER_IDS - set(ids)
    if missing_ids:
        errors.append("missing required layer ids: " + ",".join(sorted(missing_ids)))

    missing_domains = REQUIRED_DOMAINS - set(domains)
    if missing_domains:
        errors.append("missing required domains: " + ",".join(sorted(missing_domains)))

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate ecosystem safety/resource stack.")
    parser.add_argument(
        "--stack",
        default="memory/FRONT/ECOSYSTEM_SAFETY_RESOURCE_STACK_V1.json",
        help="Path to stack JSON.",
    )
    args = parser.parse_args(argv)

    path = Path(args.stack).resolve()
    if not path.exists():
        print(f"SAFETY_STACK_FAIL: file not found: {path}")
        return 2

    try:
        data = load_stack(path)
        errors = validate_stack(data)
    except Exception as exc:  # pragma: no cover
        print(f"SAFETY_STACK_FAIL: {exc}")
        return 2

    if errors:
        for error in errors:
            print(f"SAFETY_STACK_FAIL: {error}")
        return 1

    print(f"SAFETY_STACK_OK layers={len(data['layers'])} file={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
