import asyncio
import json
import os
from core.mcp.core_lib import SovereignMCPCore, MCPJSONRPCAdapter
from security.agent_monitor import AgentThoughtMonitor, MCPSecurityProtocol

class SovereignMCPGateway:
    """
    Гейтвей для управления локальными и внешними MCP вызовами.
    Выполняет роль оркестратора и защитника.
    """
    def __init__(self, system_id: str = "RADR-01"):
        self.hub = SovereignMCPCore(system_id)
        self.adapter = MCPJSONRPCAdapter()
        self.security = MCPSecurityProtocol()
        self.monitor = AgentThoughtMonitor()
        self.is_local_only = True # По умолчанию работаем в полностью локальном режиме
        
    def register_default_tools(self):
        """Регистрация базовых инструментов экосистемы."""
        self.hub.register_tool(
            "read_system_logs",
            "Reads latest system logs from the bridge.",
            {"type": "object", "properties": {"lines": {"type": "number", "default": 10}}},
            self._handle_read_logs
        )
        
    def _handle_read_logs(self, args: dict):
        lines = args.get("lines", 10)
        with open("DEV_LOGS.md", "r") as f:
            return f.readlines()[-lines:]

    async def process_external_request(self, json_rpc_request: dict):
        """Обработка внешнего JSON-RPC запроса от других MCP систем."""
        method = json_rpc_request.get("method")
        params = json_rpc_request.get("params", {})
        request_id = json_rpc_request.get("id")
        
        # 1. Безопасность: Проверка инъекции через SGRD
        is_safe, msg = self.security.validate_injection(str(method) + str(params), "MCP_GATEWAY_ACTIVE")
        if not is_safe:
            return self.adapter.wrap_response({"error": msg}, request_id)
            
        # 2. Роутинг
        if method == "tools/list":
            result = {"tools": self.hub.list_tools()}
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            
            # Логируем мысль/интент через монитор
            self.monitor.capture_thought_chain("external-agent", f"Calling tool {tool_name} with {tool_args}")
            
            result = await self.hub.call_tool(tool_name, tool_args)
        else:
            result = {"error": f"Method {method} not supported."}
            
        return self.adapter.wrap_response(result, request_id)

async def main():
    gateway = SovereignMCPGateway()
    gateway.register_default_tools()
    
    # Симуляция внешнего запроса на список инструментов
    req = MCPJSONRPCAdapter.wrap_request("tools/list", {})
    response = await gateway.process_external_request(req)
    print("MCP Gateway Tools List Response:")
    print(json.dumps(response, indent=2))
    
    # Симуляция вызова инструмента
    call_req = MCPJSONRPCAdapter.wrap_request("tools/call", {"name": "read_system_logs", "arguments": {"lines": 2}})
    call_res = await gateway.process_external_request(call_req)
    print("\nMCP Gateway Tool Call Response:")
    print(json.dumps(call_res, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
