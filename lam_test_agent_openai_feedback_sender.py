from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def post_bundle(upload_url: str, payload: dict[str, Any], timeout_sec: int, api_key: str = "") -> tuple[int, str]:
    body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = request.Request(upload_url, data=body, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=timeout_sec) as resp:
            code = int(getattr(resp, "status", 0) or 0)
            preview = resp.read(1500).decode("utf-8", errors="ignore")
            return code, preview
    except error.HTTPError as exc:
        body_preview = exc.read(1500).decode("utf-8", errors="ignore")
        return int(exc.code), body_preview
    except Exception as exc:
        return 0, f"{type(exc).__name__}: {exc}"


def write_spool(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def write_receipt(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Send OpenAI feedback bundle with spool fallback.")
    parser.add_argument("--bundle-json", default="memory/FRONT/OPENAI_FEEDBACK_BUNDLE.json")
    parser.add_argument("--spool-dir", default=".gateway/feedback_spool")
    parser.add_argument("--receipts-dir", default=".gateway/receipts")
    parser.add_argument("--upload-url", default=os.environ.get("OPENAI_DEBUG_UPLOAD_URL", ""))
    parser.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY", ""))
    parser.add_argument("--timeout-sec", type=int, default=int(os.environ.get("OPENAI_DEBUG_TIMEOUT_SEC", "60")))
    args = parser.parse_args(argv)

    bundle_path = Path(args.bundle_json).resolve()
    spool_dir = Path(args.spool_dir).resolve()
    receipts_dir = Path(args.receipts_dir).resolve()

    if not bundle_path.exists():
        print(f"OPENAI_FEEDBACK_SEND_FAIL missing_bundle={bundle_path}")
        return 2

    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    if not isinstance(bundle, dict):
        print("OPENAI_FEEDBACK_SEND_FAIL bundle_not_object")
        return 2

    incidents = bundle.get("incidents")
    if not isinstance(incidents, list) or not incidents:
        print("OPENAI_FEEDBACK_SEND_OK incidents=0 critical=0 reason=no_incidents")
        return 0

    ev_id = bundle_event_id(bundle)
    crit = critical_count(bundle)
    spool_file = spool_dir / f"feedback_{ev_id}.json"

    if not args.upload_url:
        spool_doc = {
            "event_id": ev_id,
            "critical_count": crit,
            "reason": "missing_upload_url",
            "created_at_utc": now_utc(),
            "bundle_path": str(bundle_path),
            "bundle": bundle,
        }
        write_spool(spool_file, spool_doc)
        if crit > 0:
            print(f"OPENAI_FEEDBACK_SEND_FAIL critical_unsent={crit} reason=missing_upload_url spool={spool_file}")
            return 1
        print(f"OPENAI_FEEDBACK_SEND_OK critical=0 reason=missing_upload_url_noncritical spool={spool_file}")
        return 0

    payload = {
        "source": "LAM_Test_Agent",
        "event_id": ev_id,
        "bundle": bundle,
    }
    status, preview = post_bundle(args.upload_url, payload, max(args.timeout_sec, 5), args.api_key)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    receipt = {
        "ts_utc": now_utc(),
        "event_id": ev_id,
        "critical_count": crit,
        "upload_url": args.upload_url,
        "http_status": status,
        "ok": 200 <= status < 300,
        "response_preview": preview,
        "bundle_path": str(bundle_path),
    }
    receipt_path = receipts_dir / f"openai_feedback_receipt_{ts}_{ev_id[:12]}.json"
    write_receipt(receipt_path, receipt)

    if receipt["ok"]:
        if spool_file.exists():
            spool_file.unlink()
        print(f"OPENAI_FEEDBACK_SEND_OK status={status} critical={crit} receipt={receipt_path}")
        return 0

    spool_doc = {
        "event_id": ev_id,
        "critical_count": crit,
        "reason": f"http_status_{status}",
        "created_at_utc": now_utc(),
        "bundle_path": str(bundle_path),
        "bundle": bundle,
    }
    write_spool(spool_file, spool_doc)
    if crit > 0:
        print(
            "OPENAI_FEEDBACK_SEND_FAIL "
            f"critical_unsent={crit} status={status} spool={spool_file} receipt={receipt_path}"
        )
        return 1

    print(f"OPENAI_FEEDBACK_SEND_OK critical=0 noncritical_send_failed status={status} spool={spool_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
