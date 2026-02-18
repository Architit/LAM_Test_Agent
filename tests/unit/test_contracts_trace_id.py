from __future__ import annotations

import pytest

from lam_test_agent_contracts import is_valid_trace_id


@pytest.mark.unit
@pytest.mark.parametrize(
    "value",
    [
        "abc",
        "trace-123",
        "trace_123",
        "trace:segment",
        "trace.segment",
        "a" * 128,
    ],
)
def test_is_valid_trace_id_accepts_expected_format(value: str) -> None:
    assert is_valid_trace_id(value)


@pytest.mark.unit
@pytest.mark.parametrize(
    "value",
    [
        "",
        "ab",
        "a" * 129,
        "bad space",
        "bad/slash",
        None,
        1,
        {},
    ],
)
def test_is_valid_trace_id_rejects_invalid_format(value) -> None:
    assert not is_valid_trace_id(value)
