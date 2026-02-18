from __future__ import annotations

import json
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any


_LOG_FILE = Path("memory/FRONT/LAM_RUNTIME_LOG.jsonl")
_EXTERNAL_DEBUG_DIR_ENV = "LAM_EXTERNAL_DEBUG_LOG_DIR"
_EXTERNAL_DEBUG_FILE = "codex_openai_codefix_debug.jsonl"


def _write_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=True) + "\n")


def _external_debug_log_file() -> Path | None:
    raw = os.environ.get(_EXTERNAL_DEBUG_DIR_ENV, "").strip()
    if not raw:
        return None
    return Path(raw) / _EXTERNAL_DEBUG_FILE


def _should_mirror_external_debug(level: str, channel: str, fields: dict[str, Any]) -> bool:
    if level.lower() != "debug":
        return False
    if channel.startswith("comm.external.") or channel.startswith("codex.bridge.external."):
        return True
    system = str(fields.get("external_system", "")).lower()
    return system in {"codex_openai", "openai_codex", "openai"}


def log(level: str, channel: str, message: str, **fields: Any) -> None:
    payload = {
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "channel": channel,
        "message": message,
        "fields": fields,
    }
    _write_jsonl(_LOG_FILE, payload)

    if not _should_mirror_external_debug(level, channel, fields):
        return

    external_file = _external_debug_log_file()
    if external_file is None:
        return

    try:
        _write_jsonl(external_file, payload)
    except OSError:
        # External debug mirror is best-effort and must never break runtime flow.
        return
