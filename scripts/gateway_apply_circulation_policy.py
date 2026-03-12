#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Apply data circulation policy template to gateway routing policy.")
    parser.add_argument(
        "--policy-file",
        default=str(root / ".gateway" / "routing_policy.json"),
        help="Path to routing_policy.json",
    )
    parser.add_argument(
        "--template",
        default=str(root / "infra" / "governance" / "GATEWAY_CIRCULATION_POLICY_TEMPLATE.json"),
        help="Path to circulation policy template JSON",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print merged JSON and do not write.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    policy_file = Path(args.policy_file).resolve()
    template_file = Path(args.template).resolve()
    if not template_file.exists():
        raise FileNotFoundError(f"template not found: {template_file}")

    policy = {}
    if policy_file.exists():
        policy = json.loads(policy_file.read_text(encoding="utf-8"))

    template = json.loads(template_file.read_text(encoding="utf-8"))
    circulation = template.get("data_circulation", {})
    if not isinstance(circulation, dict):
        raise RuntimeError("template.data_circulation must be an object")

    policy["data_circulation"] = circulation
    rendered = json.dumps(policy, ensure_ascii=True, indent=2) + "\n"
    if args.dry_run:
        print(rendered)
        return 0

    policy_file.parent.mkdir(parents=True, exist_ok=True)
    policy_file.write_text(rendered, encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "ok",
                "policy_file": str(policy_file),
                "template": str(template_file),
                "updated_key": "data_circulation",
            },
            ensure_ascii=True,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
