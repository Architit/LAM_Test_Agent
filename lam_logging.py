from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_LOG_FILE = Path("memory/FRONT/LAM_RUNTIME_LOG.jsonl")


def log(level: str, channel: str, message: str, **fields: Any) -> None:
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "channel": channel,
        "message": message,
        "fields": fields,
    }
    with _LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=True) + "\n")
