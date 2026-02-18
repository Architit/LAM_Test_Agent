from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXTERNAL_SYSTEMS = {"codex_openai", "openai_codex", "openai"}
REDACT_KEYS = {
    "authorization",
    "token",
    "api_key",
    "apikey",
    "secret",
    "password",
    "bearer",
    "openai_api_key",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def iter_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def _lower(s: Any) -> str:
    return str(s or "").lower()


def is_external_debug_event(ev: dict[str, Any]) -> bool:
    channel = _lower(ev.get("channel"))
    if channel.startswith("comm.external.") or channel.startswith("codex.bridge.external."):
        return True
    fields = ev.get("fields")
    if not isinstance(fields, dict):
        return False
    return _lower(fields.get("external_system")) in EXTERNAL_SYSTEMS


def classify_severity(ev: dict[str, Any]) -> str:
    level = _lower(ev.get("level"))
    fields = ev.get("fields")
    if not isinstance(fields, dict):
        fields = {}
    ok = fields.get("ok")
    err = _lower(fields.get("error"))
    if level in {"critical", "fatal"}:
        return "critical"
    if level == "error":
        return "critical"
    if ok is False or err:
        return "critical"
    if level == "warning" or level == "warn":
        return "high"
    return "info"


def sanitize_value(value: Any, parent_key: str = "") -> Any:
    k = _lower(parent_key)
    if any(tag in k for tag in REDACT_KEYS):
        return "<redacted>"

    if isinstance(value, dict):
        return {str(x): sanitize_value(y, str(x)) for x, y in value.items()}
    if isinstance(value, list):
        return [sanitize_value(v, parent_key) for v in value]
    if isinstance(value, str):
        v = value
        if "bearer " in v.lower():
            return "<redacted>"
        if len(v) > 1200:
            return v[:1200] + "...<truncated>"
        return v
    return value


def event_fingerprint(ev: dict[str, Any]) -> str:
    fields = ev.get("fields")
    if not isinstance(fields, dict):
        fields = {}
    sig = {
        "channel": ev.get("channel"),
        "message": ev.get("message"),
        "external_system": fields.get("external_system"),
        "intent": fields.get("intent"),
        "action": fields.get("action"),
        "operation": fields.get("operation"),
        "error": fields.get("error"),
    }
    blob = json.dumps(sig, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def build_bundle(events: list[dict[str, Any]], source: Path, max_incidents: int = 200) -> dict[str, Any]:
    external = [ev for ev in events if is_external_debug_event(ev)]
    grouped: dict[str, dict[str, Any]] = {}

    for ev in external:
        fp = event_fingerprint(ev)
        sev = classify_severity(ev)
        ts = str(ev.get("ts_utc") or "")
        fields = ev.get("fields")
        if not isinstance(fields, dict):
            fields = {}

        row = grouped.get(fp)
        if row is None:
            row = {
                "incident_id": fp[:16],
                "fingerprint": fp,
                "count": 0,
                "severity": sev,
                "first_seen_utc": ts,
                "last_seen_utc": ts,
                "channel": ev.get("channel"),
                "message": ev.get("message"),
                "external_system": fields.get("external_system"),
                "error": fields.get("error"),
                "intent": fields.get("intent"),
                "action": fields.get("action"),
                "operation": fields.get("operation"),
                "sample": sanitize_value(ev),
            }
            grouped[fp] = row

        row["count"] += 1
        if ts and (not row["first_seen_utc"] or ts < row["first_seen_utc"]):
            row["first_seen_utc"] = ts
        if ts and (not row["last_seen_utc"] or ts > row["last_seen_utc"]):
            row["last_seen_utc"] = ts

        if row["severity"] != "critical" and sev == "critical":
            row["severity"] = "critical"

    incidents = sorted(grouped.values(), key=lambda x: (-int(x["count"]), str(x["severity"])))
    incidents = incidents[:max_incidents]

    critical = sum(1 for x in incidents if x.get("severity") == "critical")
    high = sum(1 for x in incidents if x.get("severity") == "high")

    return {
        "generated_at_utc": now_utc(),
        "source_file": str(source),
        "total_events": len(events),
        "external_events": len(external),
        "summary": {
            "incidents": len(incidents),
            "critical_incidents": critical,
            "high_incidents": high,
        },
        "incidents": incidents,
    }


def render_md(bundle: dict[str, Any]) -> str:
    s = bundle.get("summary", {}) if isinstance(bundle, dict) else {}
    lines = [
        "# OPENAI_FEEDBACK_BUNDLE",
        "",
        f"- generated_at_utc: {bundle.get('generated_at_utc')}",
        f"- source_file: {bundle.get('source_file')}",
        f"- total_events: {bundle.get('total_events')}",
        f"- external_events: {bundle.get('external_events')}",
        f"- incidents: {s.get('incidents', 0)}",
        f"- critical_incidents: {s.get('critical_incidents', 0)}",
        f"- high_incidents: {s.get('high_incidents', 0)}",
        "",
        "## Top Incidents",
        "",
        "| severity | count | channel | error | external_system | incident_id |",
        "|---|---:|---|---|---|---|",
    ]

    incidents = bundle.get("incidents")
    if isinstance(incidents, list):
        for item in incidents[:50]:
            if not isinstance(item, dict):
                continue
            lines.append(
                f"| {item.get('severity','')} | {item.get('count',0)} | {item.get('channel','')} | {item.get('error','')} | {item.get('external_system','')} | {item.get('incident_id','')} |"
            )

    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build sanitized OpenAI feedback bundle from debug logs.")
    parser.add_argument("--input", default=".gateway/external_debug/codex_openai_codefix_debug.jsonl")
    parser.add_argument("--output-json", default="memory/FRONT/OPENAI_FEEDBACK_BUNDLE.json")
    parser.add_argument("--output-md", default="memory/FRONT/OPENAI_FEEDBACK_BUNDLE.md")
    parser.add_argument("--max-incidents", type=int, default=200)
    args = parser.parse_args(argv)

    input_path = Path(args.input).resolve()
    out_json = Path(args.output_json).resolve()
    out_md = Path(args.output_md).resolve()

    events = iter_jsonl(input_path)
    bundle = build_bundle(events, input_path, max_incidents=max(args.max_incidents, 1))

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(bundle, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(render_md(bundle), encoding="utf-8")

    summary = bundle.get("summary", {})
    print(
        "OPENAI_FEEDBACK_BUNDLE_OK "
        f"input={input_path} incidents={summary.get('incidents',0)} "
        f"critical={summary.get('critical_incidents',0)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
