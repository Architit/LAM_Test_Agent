# -*- coding: utf-8 -*-
"""Unified Logging System for LAM (HEALED - Phase 8.0)."""

from __future__ import annotations

import json
import os
import logging
from datetime import datetime, timezone
from typing import Any, Dict
from contextvars import ContextVar

_lam_ctx: ContextVar[dict] = ContextVar("lam_ctx", default={})

def set_context(**ctx: Any) -> None:
    cur = dict(_lam_ctx.get() or {})
    cur.update({k: v for k, v in ctx.items() if v is not None})
    _lam_ctx.set(cur)

def clear_context() -> None:
    _lam_ctx.set({})

def _inject_context(fields: Dict[str, Any]) -> Dict[str, Any]:
    cur = _lam_ctx.get() or {}
    for k in ("trace_id", "task_id", "parent_task_id", "span_id"):
        if k not in fields and k in cur:
            fields[k] = cur[k]
    return fields

def _level_value(level: str) -> int:
    level = (level or "").lower()
    return {
        "error": 40, "warn": 30, "warning": 30,
        "info": 20, "debug": 10, "trace": 5,
    }.get(level, 30)

def should_log(level: str, *, event: str | None = None) -> bool:
    cur = os.getenv("LAM_LOG_LEVEL", "info") # Повышаем до info для чистоты встречи
    if _level_value(level) < _level_value(cur):
        return False
    allow = os.getenv("LAM_LOG_EVENTS", "").strip()
    if allow and event:
        allowed = {x.strip().lower() for x in allow.split(",") if x.strip()}
        return event.lower() in allowed
    return True

def log(level: str, event: str, msg: str, **fields: Any) -> None:
    """Canonical one-line JSON logger."""
    if not should_log(level, event=event):
        return
    fields = _inject_context(dict(fields))
    payload: Dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": level.lower(),
        "event": event,
        "msg": msg,
        **fields,
    }
    # Используем системный stdout для единства потока
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))

class UnifiedLoggingHandler(logging.Handler):
    """Adapter to route standard python logs through lam_logging.log()"""
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level_map = {
                logging.DEBUG: "debug",
                logging.INFO: "info",
                logging.WARNING: "warn",
                logging.ERROR: "error",
                logging.CRITICAL: "error"
            }
            log(
                level=level_map.get(record.levelno, "info"),
                event=f"sys.{record.name}",
                msg=record.getMessage(),
                logger_name=record.name,
                pathname=record.pathname,
                lineno=record.lineno
            )
        except Exception:
            self.handleError(record)

def setup_global_redirection():
    """Redirect all standard logs to UnifiedLoggingHandler."""
    root_logger = logging.getLogger()
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)
    root_logger.addHandler(UnifiedLoggingHandler())
    root_logger.setLevel(logging.INFO)
