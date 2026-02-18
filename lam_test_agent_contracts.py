from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping


TRACE_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{3,128}$")


@dataclass(frozen=True)
class PingPongEnvelope:
    status: str
    reply: str
    trace_id: str | None


def validate_ping_payload(payload: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["payload must be dict"]
    msg = payload.get("msg")
    if not isinstance(msg, str):
        errors.append("msg must be string")
    elif not msg.strip():
        errors.append("msg must be non-empty")
    intent = payload.get("intent")
    if intent is not None and not isinstance(intent, str):
        errors.append("intent must be string when provided")
    trace_id = payload.get("trace_id")
    if trace_id is not None and not is_valid_trace_id(trace_id):
        errors.append("trace_id has invalid format")
    return errors


def is_valid_trace_id(value: Any) -> bool:
    return isinstance(value, str) and bool(TRACE_ID_RE.match(value))


def normalize_ping_pong_reply(raw: Any) -> PingPongEnvelope:
    if raw == "pong":
        return PingPongEnvelope(status="ok", reply="pong", trace_id=None)

    if not isinstance(raw, Mapping):
        raise ValueError("reply must be 'pong' string or mapping envelope")

    status = raw.get("status", "ok")
    if status not in {"ok", "error"}:
        raise ValueError("status must be 'ok' or 'error'")

    reply = raw.get("reply")
    if not isinstance(reply, str) or not reply.strip():
        raise ValueError("reply must be non-empty string")

    trace_id = raw.get("trace_id")
    if trace_id is not None and not is_valid_trace_id(trace_id):
        raise ValueError("trace_id has invalid format")

    return PingPongEnvelope(status=status, reply=reply, trace_id=trace_id)
