from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def bundle_event_id(bundle: dict[str, Any]) -> str:
    blob = json.dumps(bundle, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def critical_count(bundle: dict[str, Any]) -> int:
    summary = bundle.get("summary") if isinstance(bundle, dict) else None
    if not isinstance(summary, dict):
        return 0
    value = summary.get("critical_incidents", 0)
    try:
        return int(value)
    except Exception:
        return 0


def pending_critical_from_spool(spool_dir: Path) -> tuple[int, list[Path]]:
    if not spool_dir.exists():
        return 0, []
    total = 0
    files: list[Path] = []
    for p in sorted(spool_dir.glob("feedback_*.json")):
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            total += 1
            files.append(p)
            continue
        c = obj.get("critical_count", 0)
        try:
            c = int(c)
        except Exception:
            c = 1
        if c > 0:
            total += c
            files.append(p)
    return total, files


def receipt_exists_for_event(receipts_dir: Path, event_id: str) -> bool:
    if not receipts_dir.exists():
        return False
    for p in sorted(receipts_dir.glob("openai_feedback_receipt_*.json")):
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if doc.get("event_id") == event_id and bool(doc.get("ok")):
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail CI when critical feedback incidents are unsent.")
    parser.add_argument("--bundle-json", default="memory/FRONT/OPENAI_FEEDBACK_BUNDLE.json")
    parser.add_argument("--spool-dir", default=".gateway/feedback_spool")
    parser.add_argument("--receipts-dir", default=".gateway/receipts")
    args = parser.parse_args(argv)

    bundle_path = Path(args.bundle_json).resolve()
    spool_dir = Path(args.spool_dir).resolve()
    receipts_dir = Path(args.receipts_dir).resolve()

    if not bundle_path.exists():
        print(f"FEEDBACK_DELIVERY_GATE_FAIL missing_bundle={bundle_path}")
        return 2

    try:
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"FEEDBACK_DELIVERY_GATE_FAIL invalid_bundle_json error={type(exc).__name__}")
        return 2
    if not isinstance(bundle, dict):
        print("FEEDBACK_DELIVERY_GATE_FAIL bundle_not_object")
        return 2

    crit = critical_count(bundle)
    ev_id = bundle_event_id(bundle)
    pending_crit, pending_files = pending_critical_from_spool(spool_dir)
    delivered = receipt_exists_for_event(receipts_dir, ev_id)

    if pending_crit > 0:
        print(
            "FEEDBACK_DELIVERY_GATE_FAIL "
            f"pending_critical={pending_crit} pending_files={len(pending_files)}"
        )
        for p in pending_files[:20]:
            print(f"FEEDBACK_DELIVERY_GATE_FAIL pending_file={p}")
        return 1

    if crit > 0 and not delivered:
        print(
            "FEEDBACK_DELIVERY_GATE_FAIL "
            f"critical_incidents={crit} delivered=false event_id={ev_id}"
        )
        return 1

    print(
        "FEEDBACK_DELIVERY_GATE_OK "
        f"critical_incidents={crit} delivered={str(delivered).lower()} pending_critical={pending_crit}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
