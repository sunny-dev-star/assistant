"""
MCP Client - 连接外部 MCP Server，发现并注册工具

MCP (Model Context Protocol) 允许框架接入任何兼容 MCP 的工具服务。
支持 stdio 和 SSE 两种传输方式。

配置 (.env):
MCP_ENABLED=true
MCP_SERVERS=[{"name":"weather-mcp","command":"python3","args":["server.py"]}]
"""
import json
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class MCPServerConfig:
    """MCP Server 配置"""
    def __init__(self, name: str, transport: str = "stdio",
                 command: str = "", args: List[str] = None,
                 env: Dict[str, str] = None, cwd: str = None, url: str = ""):
        self.name = name
        self.transport = transport
        self.command = command
        self.args = args or []
        self.env = env
        self.cwd = cwd
        self.url = url
        self.tools: List[dict] = []

    @classmethod
    def from_dict(cls, d: dict) -> "MCPServerConfig":
        return cls(name=d.get("name", "unknown"), transport=d.get("transport", "stdio"),
                   command=d.get("command", ""), args=d.get("args", []),
                   env=d.get("env"), cwd=d.get("cwd"), url=d.get("url", ""))


class MCPClient:
    """MCP 客户端 - 启动时发现工具，调用时重新连接"""

    def __init__(self):
        self._servers: Dict[str, MCPServerConfig] = {}
        self._tool_to_server: Dict[str, str] = {}
        self._tools: List[dict] = []

    async def connect_servers_from_config(self, config: List[dict]):
        for item in config:
            cfg = MCPServerConfig.from_dict(item)
            self._servers[cfg.name] = cfg
            try:
                if cfg.transport == "sse" and cfg.url:
                    tools = await self._discover_sse(cfg)
                else:
                    tools = await self._discover_stdio(cfg)
                cfg.tools = tools
                for t in tools:
                    self._tool_to_server[t["function"]["name"]] = cfg.name
                self._tools.extend(tools)
                logger.info(f"✅ MCP '{cfg.name}': {len(tools)} tools")
            except Exception as e:
                logger.error(f"❌ MCP '{cfg.name}' discover failed: {e}")

    async def _discover_stdio(self, cfg: MCPServerConfig) -> List[dict]:
        from mcp import StdioServerParameters, ClientSession
        from mcp.client.stdio import stdio_client
        params = StdioServerParameters(command=cfg.command, args=cfg.args, env=cfg.env, cwd=cfg.cwd)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                return self._tools_to_openai(result.tools)

    async def _discover_sse(self, cfg: MCPServerConfig) -> List[dict]:
        from mcp import ClientSession
        from mcp.client.sse import sse_client
        async with sse_client(cfg.url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                return self._tools_to_openai(result.tools)

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        server_name = self._tool_to_server.get(tool_name)
        if not server_name:
            return json.dumps({"error": f"MCP tool not found: {tool_name}"}, ensure_ascii=False)
        cfg = self._servers[server_name]
        try:
            if cfg.transport == "sse" and cfg.url:
                return await self._call_sse(cfg, tool_name, arguments)
            else:
                return await self._call_stdio(cfg, tool_name, arguments)
        except Exception as e:
            logger.error(f"MCP call_tool({tool_name}) failed: {e}")
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    async def _call_stdio(self, cfg: MCPServerConfig, tool_name: str, args: dict) -> str:
        from mcp import StdioServerParameters, ClientSession
        from mcp.client.stdio import stdio_client
        params = StdioServerParameters(command=cfg.command, args=cfg.args, env=cfg.env, cwd=cfg.cwd)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, args)
                return self._extract_result(result)

    async def _call_sse(self, cfg: MCPServerConfig, tool_name: str, args: dict) -> str:
        from mcp import ClientSession
        from mcp.client.sse import sse_client
        async with sse_client(cfg.url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, args)
                return self._extract_result(result)

    def _extract_result(self, result) -> str:
        texts = []
        for content in (result.content or []):
            if hasattr(content, "text"):
                texts.append(content.text)
            else:
                texts.append(str(content))
        return "\n".join(texts) if texts else json.dumps(
            {"result": "ok", "isError": result.isError}, ensure_ascii=False)

    @staticmethod
    def _tools_to_openai(tools) -> List[dict]:
        return [{
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": t.inputSchema or {"type": "object", "properties": {}},
            }
        } for t in tools]

    def get_tools(self) -> List[dict]:
        return self._tools

    def get_server_info(self) -> List[dict]:
        return [{"name": c.name, "transport": c.transport, "tools_count": len(c.tools)}
                for c in self._servers.values()]

    @property
    def tool_count(self): return len(self._tools)
    @property
    def server_count(self): return len(self._servers)

    async def cleanup(self):
        """Cleanup MCP connections"""
        self._servers.clear()
        self._tools.clear()
        self._tool_to_server.clear()
