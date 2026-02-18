from __future__ import annotations

import pytest

from lam_test_agent_contracts import PingPongEnvelope, normalize_ping_pong_reply


@pytest.mark.unit
def test_normalize_ping_reply_from_plain_string() -> None:
    out = normalize_ping_pong_reply("pong")
    assert out == PingPongEnvelope(status="ok", reply="pong", trace_id=None)


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw",
    [
        {"reply": "pong"},
        {"status": "ok", "reply": "pong"},
        {"status": "ok", "reply": "pong", "trace_id": "trace-1"},
        {"status": "error", "reply": "pong"},
    ],
)
def test_normalize_ping_reply_from_mapping(raw: dict) -> None:
    out = normalize_ping_pong_reply(raw)
    assert out.reply == "pong"
    assert out.status in {"ok", "error"}


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw,error_msg",
    [
        (None, "mapping envelope"),
        (123, "mapping envelope"),
        ({}, "reply must be non-empty string"),
        ({"reply": ""}, "reply must be non-empty string"),
        ({"reply": "pong", "status": "unknown"}, "status must be 'ok' or 'error'"),
        ({"reply": "pong", "trace_id": "x"}, "trace_id has invalid format"),
    ],
)
def test_normalize_ping_reply_rejects_invalid_envelope(raw, error_msg: str) -> None:
    with pytest.raises(ValueError, match=error_msg):
        normalize_ping_pong_reply(raw)
