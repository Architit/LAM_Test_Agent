from __future__ import annotations

import json
from pathlib import Path

import pytest

from lam_test_agent_openai_feedback_bundle import build_bundle, iter_jsonl, render_md


@pytest.mark.unit
def test_build_bundle_classifies_critical_and_sanitizes(tmp_path: Path) -> None:
    log = tmp_path / "debug.jsonl"
    events = [
        {
            "ts_utc": "2026-02-18T00:00:00Z",
            "level": "debug",
            "channel": "codex.bridge.external.debug",
            "message": "bridge.send_outbound",
            "fields": {
                "ok": False,
                "error": "enqueue_failed",
                "external_system": "codex_openai",
                "api_key": "sk-secret",
            },
        },
        {
            "ts_utc": "2026-02-18T00:00:10Z",
            "level": "debug",
            "channel": "codex.bridge.external.debug",
            "message": "bridge.send_outbound",
            "fields": {
                "ok": False,
                "error": "enqueue_failed",
                "external_system": "codex_openai",
                "api_key": "sk-secret",
            },
        },
    ]
    log.write_text("\n".join(json.dumps(x) for x in events) + "\n", encoding="utf-8")

    parsed = iter_jsonl(log)
    bundle = build_bundle(parsed, log)

    assert bundle["summary"]["incidents"] == 1
    assert bundle["summary"]["critical_incidents"] == 1
    incident = bundle["incidents"][0]
    assert incident["count"] == 2
    assert incident["severity"] == "critical"
    assert incident["sample"]["fields"]["api_key"] == "<redacted>"


@pytest.mark.unit
def test_render_md_contains_top_table(tmp_path: Path) -> None:
    log = tmp_path / "debug.jsonl"
    log.write_text("", encoding="utf-8")
    bundle = build_bundle([], log)
    md = render_md(bundle)
    assert "OPENAI_FEEDBACK_BUNDLE" in md
    assert "| severity | count |" in md
