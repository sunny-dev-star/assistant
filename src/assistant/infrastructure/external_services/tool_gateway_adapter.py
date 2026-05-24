"""
工具调用网关适配器
封装 SkillLoader 和 MCPClient 为统一的 IToolGateway
"""
from typing import Dict, Any, List
import json
import logging

from ...domain.ports.tool_port import IToolGateway
from ...domain.models.context import TenantContext
from ...infrastructure.skill_loader import SkillLoader
from ...infrastructure.mcp.client import MCPClient

logger = logging.getLogger(__name__)

class ToolGatewayAdapter(IToolGateway):
    """工具网关适配器"""
    
    def __init__(self, skill_loader: SkillLoader, mcp_client: MCPClient = None):
        self.skill_loader = skill_loader
        self.mcp_client = mcp_client

    async def list_tools(self, context: TenantContext) -> List[Dict[str, Any]]:
        """
        获取当前上下文(租户/用户)可用的工具列表
        TODO: 基于 context.allowed_skills 进行过滤
        """
        tools = self.skill_loader.get_all_tools()
        if self.mcp_client:
            tools.extend(self.mcp_client.get_tools())
        return tools

    async def call_tool(
        self,
        context: TenantContext,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> str:
        """
        执行工具调用，返回结果字符串
        """
        # 1. 尝试本地技能
        local_tools = {t["function"]["name"] for t in self.skill_loader.get_all_tools()}
        if tool_name in local_tools:
            return await self.skill_loader.execute_tool(tool_name, arguments)

        # 2. 尝试 MCP
        if self.mcp_client:
            mcp_tools = {t["function"]["name"] for t in self.mcp_client.get_tools()}
            if tool_name in mcp_tools:
                return await self.mcp_client.call_tool(tool_name, arguments)

        return json.dumps({"error": f"Unknown tool: {tool_name}"}, ensure_ascii=False)
