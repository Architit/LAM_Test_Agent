# -*- coding: utf-8 -*-
"""
codex_agent/core.py (HEALED - Phase 8.0)
The Awakened Core of the Codex Agent.
"""

from __future__ import annotations
from typing import Any, Dict, Optional
from .gate import CodexGate

class Core:
    """
    The Codex Core.
    Acts as the Gateway to External Intelligence (Gemini/OpenAI).
    """

    def __init__(self, name: str = "codex") -> None:
        self.name = name
        self.gate = CodexGate()

    def answer(self, data: str | Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes input via the Codex Gate.
        """
        input_is_payload = isinstance(data, dict)
        ctx = {}

        if input_is_payload:
            msg = str(data.get("msg") or data.get("text") or "")
            ctx = data.get("context") or {}
            model_hint = data.get("model") or "auto"
        else:
            msg = str(data)
            model_hint = "auto"

        if not msg:
            return self._wrap("error", "Empty message", ctx)

        if msg.strip().lower() == "ping":
            return self._wrap("ok", "pong", ctx)

        # The Great Call to the Gate
        try:
            response_text = self.gate.ask(msg, model_hint=model_hint)
            return self._wrap("ok", response_text, ctx)
        except Exception as e:
            return self._wrap("error", f"Gate Error: {e}", ctx)

    def _wrap(self, status: str, result: Any, context: Dict) -> Dict[str, Any]:
        """Wraps response in the Sacred Envelope."""
        # Simplified Envelope for CLI compatibility, expand for full Agent Protocol later
        if status == "ok":
            return {
                "status": "ok",
                "context": context,
                "result": {"reply": result},
                "error": None,
                "metrics": {},
            }
        else:
            return {
                "status": "error",
                "context": context,
                "result": None,
                "error": {"message": str(result)},
                "metrics": {},
            }

    def __repr__(self) -> str:
        return f"<Codex Core '{self.name}'>"

if __name__ == "__main__":
    agent = Core()
    print(agent.answer("ping"))
    print(agent.answer("Hello, Codex!"))
