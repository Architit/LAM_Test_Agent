import json
import uuid
from typing import Callable, Dict, Any, List

class SovereignMCPCore:
    """
    Sovereign MCP Core Library (Python).
    Локальная библиотека для регистрации и управления MCP инструментами и ресурсами.
    """
    def __init__(self, system_id: str):
        self.system_id = system_id
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.resources: Dict[str, Any] = {}
        
    def register_tool(self, name: str, description: str, schema: dict, handler: Callable):
        """Регистрация нового инструмента в локальном хабе."""
        self.tools[name] = {
            "name": name,
            "description": description,
            "inputSchema": schema,
            "handler": handler
        }
        
    def list_tools(self) -> List[dict]:
        """Возвращает список доступных инструментов в формате MCP."""
        return [
            {k: v for k, v in tool.items() if k != "handler"}
            for tool in self.tools.values()
        ]
        
    async def call_tool(self, name: str, arguments: dict) -> dict:
        """Вызывает инструмент и возвращает результат."""
        if name not in self.tools:
            return {"status": "error", "message": f"Tool '{name}' not found."}
            
        handler = self.tools[name]["handler"]
        try:
            # Вызов обработчика (поддержка как синхронных, так и асинхронных функций)
            import asyncio
            if asyncio.iscoroutinefunction(handler):
                result = await handler(arguments)
            else:
                result = handler(arguments)
            return {"status": "success", "content": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}

class MCPJSONRPCAdapter:
    """Адаптер для преобразования внутренних вызовов в JSON-RPC 2.0 (MCP стандарт)."""
    @staticmethod
    def wrap_request(method: str, params: dict, request_id: str = None) -> dict:
        return {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": request_id or str(uuid.uuid4())
        }

    @staticmethod
    def wrap_response(result: Any, request_id: str) -> dict:
        return {
            "jsonrpc": "2.0",
            "result": result,
            "id": request_id
        }
