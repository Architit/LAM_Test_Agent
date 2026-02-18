from __future__ import annotations

import pytest

from lam_test_agent_contracts import validate_ping_payload


@pytest.mark.unit
@pytest.mark.parametrize(
    "payload,expected_error",
    [
        (None, "payload must be dict"),
        ("x", "payload must be dict"),
        ([], "payload must be dict"),
        ({}, "msg must be string"),
        ({"msg": None}, "msg must be string"),
        ({"msg": 1}, "msg must be string"),
        ({"msg": ""}, "msg must be non-empty"),
        ({"msg": "   "}, "msg must be non-empty"),
        ({"msg": "ping", "intent": 1}, "intent must be string when provided"),
        ({"msg": "ping", "trace_id": "x"}, "trace_id has invalid format"),
        ({"msg": "ping", "trace_id": "bad space"}, "trace_id has invalid format"),
    ],
)
def test_validate_ping_payload_invalid(payload, expected_error: str) -> None:
    errors = validate_ping_payload(payload)
    assert expected_error in errors


@pytest.mark.unit
@pytest.mark.parametrize(
    "payload",
    [
        {"msg": "ping"},
        {"msg": "ping", "intent": "ping_pong"},
        {"msg": "ping", "trace_id": "abc-123"},
        {"msg": "ping", "intent": "chat", "trace_id": "trace_01:sub"},
    ],
)
def test_validate_ping_payload_valid(payload: dict) -> None:
    assert validate_ping_payload(payload) == []
