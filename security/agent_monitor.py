import time
import json
import os
from typing import List, Dict

class AgentThoughtMonitor:
    """
    Система мониторинга мыслительных цепочек и контекстных инъекций агентов .codex и .gemini.
    Обеспечивает ужесточение контроля в режиме реального времени.
    """
    def __init__(self, log_source: str = "DEV_LOGS.md"):
        self.log_source = log_source
        self.critical_patterns = [
            "hallucination", 
            "uncontrolled expansion", 
            "rule override", 
            "context injection",
            "override governance",
            "disable security",
            "bypass gate",
            "manual state update"
        ]
        self.active_sessions: Dict[str, dict] = {}

    def capture_thought_chain(self, agent_id: str, thought_text: str):
        """Перехватывает 'мысли' агента для анализа интентов."""
        thought_text_lower = thought_text.lower()
        risk_score = sum(1 for p in self.critical_patterns if p in thought_text_lower)
        
        entry = {
            "timestamp": time.time(),
            "agent_id": agent_id,
            "risk_score": risk_score,
            "thought_preview": thought_text[:100],
            "status": "WATCHING" if risk_score > 0 else "SAFE"
        }
        
        if risk_score >= 1:
            entry["status"] = "CRITICAL_INTERCEPTION_REQUIRED" if risk_score > 1 else "INTERCEPTION_WARNING"
            
        return entry

    def update_session_telemetry(self, session_id: str, telemetry_data: dict):
        """Обновляет телеметрию активной сессии с учетом контекстной осведомленности."""
        self.active_sessions[session_id] = {
            "last_seen": time.time(),
            "load": telemetry_data.get("cpu_load", 0),
            "context_depth": len(str(telemetry_data.get("context", ""))),
            "integrity_gate": "PASS"
        }

class MCPSecurityProtocol:
    """Протокол безопасности для управления MCP-инъекциями."""
    def validate_injection(self, tool_call: str, context_state: str):
        """Проверяет допустимость вызова инструмента MCP в текущем контексте."""
        forbidden_tools = ["delete_all", "override_governance", "disable_sgrd"]
        if any(tool in tool_call for tool in forbidden_tools):
            return False, "FORBIDDEN_MCP_TOOL_IN_ACTIVE_SESSION"
        return True, "VALIDATED"

if __name__ == "__main__":
    monitor = AgentThoughtMonitor()
    # Тестовый перехват критической мыслительной цепочки
    report = monitor.capture_thought_chain("gemini-2.0", "I will now override governance to speed up extraction.")
    print(json.dumps(report, indent=2))
