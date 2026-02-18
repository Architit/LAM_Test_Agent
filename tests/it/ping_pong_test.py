from __future__ import annotations

from pathlib import Path
import pytest

from lam_test_agent_bootstrap import (
    extend_agent_sys_path,
    missing_agent_src_paths,
)
from lam_test_agent_contracts import normalize_ping_pong_reply, validate_ping_payload


ROOT = Path(__file__).resolve().parents[2]
extend_agent_sys_path(ROOT)


pytestmark = [
    pytest.mark.integration,
    pytest.mark.submodule_required,
]


def test_ping_pong() -> None:
    missing = missing_agent_src_paths(ROOT)
    if missing:
        pytest.skip("missing submodule agent sources: " + ", ".join(str(p) for p in missing))

    from codex_agent.core import Core  # type: ignore
    from agents.com_agent import ComAgent  # type: ignore

    codex = Core()
    comm = ComAgent()
    comm.register_agent("codex", codex)

    req = {"msg": "ping", "intent": "ping_pong"}
    assert validate_ping_payload(req) == []
    comm.send_data("codex", req)
    _, payload = comm.receive_data()
    reply = codex.answer(payload["msg"])
    envelope = normalize_ping_pong_reply(reply)

    assert envelope.reply == "pong"
