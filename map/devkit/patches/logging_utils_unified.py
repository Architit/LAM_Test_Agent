# -*- coding: utf-8 -*-
"""Helper utilities for emitting unified structured logs."""

import logging
from .lam_logging import log as lam_log, UnifiedLoggingHandler

def get_json_logger(name: str) -> logging.Logger:
    """Return a standard logger that is automatically routed to lam_logging.log()"""
    logger = logging.getLogger(name)
    if not any(isinstance(h, UnifiedLoggingHandler) for h in logger.handlers):
        # Если у логгера нет нашего обработчика, добавляем его
        # Это обеспечивает, что даже старый код зазвучит в унисон
        handler = UnifiedLoggingHandler()
        logger.addHandler(handler)
        logger.propagate = False # Избегаем дублирования в root
        logger.setLevel(logging.INFO)
    return logger
