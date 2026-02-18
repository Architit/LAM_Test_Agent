from __future__ import annotations

import json
from pathlib import Path

import pytest

from lam_logging import log


@pytest.mark.unit
def test_debug_channel_can_be_mirrored_to_external_stream(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LAM_EXTERNAL_DEBUG_LOG_DIR", str(tmp_path / "ext"))

    log(
        "debug",
        "comm.external.debug",
        "external debug log for code-fix request",
        external_system="codex_openai",
        request_id="req-1",
    )

    local_file = tmp_path / "memory" / "FRONT" / "LAM_RUNTIME_LOG.jsonl"
    external_file = tmp_path / "ext" / "codex_openai_codefix_debug.jsonl"
    assert local_file.exists()
    assert external_file.exists()

    external_payload = json.loads(external_file.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert external_payload["channel"] == "comm.external.debug"
    assert external_payload["fields"]["request_id"] == "req-1"


@pytest.mark.unit
def test_non_debug_events_are_not_mirrored(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LAM_EXTERNAL_DEBUG_LOG_DIR", str(tmp_path / "ext"))

    log("info", "comm.enqueue", "enqueue", recipient="codex")

    external_file = tmp_path / "ext" / "codex_openai_codefix_debug.jsonl"
    assert not external_file.exists()
