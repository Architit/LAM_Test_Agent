from __future__ import annotations

from pathlib import Path
import importlib
import sys
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[2]
COMM_SRC = ROOT / "LAM_Test" / "agents" / "comm-agent" / "src"
CODEX_SRC = ROOT / "LAM_Test" / "agents" / "codex-agent" / "src"

if str(COMM_SRC) not in sys.path:
    sys.path.insert(0, str(COMM_SRC))
if str(CODEX_SRC) not in sys.path:
    sys.path.insert(1, str(CODEX_SRC))


@pytest.mark.unit
@pytest.mark.submodule_required
def test_send_data_emits_enqueue_record(monkeypatch: pytest.MonkeyPatch) -> None:
    comm_module = importlib.import_module("interfaces.com_agent_interface")
    ComAgent = getattr(comm_module, "ComAgent")

    captured: list[tuple[str, str, str, dict[str, Any]]] = []

    def fake_log(level: str, channel: str, message: str, **fields: Any) -> None:
        captured.append((level, channel, message, fields))

    monkeypatch.setattr(comm_module, "lam_log", fake_log)

    comm = ComAgent()
    comm.register_agent("codex", object())

    ok = comm.send_data(
        "codex",
        {
            "intent": "code_fix_request",
            "provider": "codex_openai",
            "request_id": "req-42",
            "context": {"trace_id": "trace-abc", "task_id": "task-7"},
            "code": "print('broken')",
        },
    )
    assert ok is True

    enqueue_records = [r for r in captured if r[1] == "comm.enqueue"]
    assert enqueue_records, "expected comm.enqueue record"
    _, _, _, fields = enqueue_records[-1]
    assert fields["intent"] == "code_fix_request"
    assert fields["trace_id"] == "trace-abc"
    assert fields["task_id"] == "task-7"
