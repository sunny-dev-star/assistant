"""
Tool gateway adapter — with tenant skill isolation
"""
from typing import Dict, Any, List
import json
import logging

from ...domain.ports.tool_port import IToolGateway
from ...domain.models.context import TenantContext
from ...infrastructure.skill_loader import SkillLoader
from ...infrastructure.mcp.client import MCPClient

logger = logging.getLogger(__name__)

# Platform skills are always available regardless of tenant config
PLATFORM_SKILLS = {"task_scheduler"}


class ToolGatewayAdapter(IToolGateway):
    """Tool gateway with tenant skill isolation"""

    def __init__(self, skill_loader: SkillLoader, mcp_client: MCPClient = None):
        self.skill_loader = skill_loader
        self.mcp_client = mcp_client

    async def list_tools(self, context: TenantContext) -> List[Dict[str, Any]]:
        """
        Return tools available to this tenant.
        Filters by context.allowed_skills if set, keeping platform skills always.
        """
        all_tools = self.skill_loader.get_all_tools_with_skill_tag()

        allowed = getattr(context, "allowed_skills", None) or []
        if allowed:
            allowed_set = set(allowed) | PLATFORM_SKILLS
            all_tools = [t for t in all_tools if t.get("_skill_name") in allowed_set]

        if self.mcp_client:
            all_tools.extend(self.mcp_client.get_tools())
        return all_tools

    async def call_tool(
        self,
        context: TenantContext,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> str:
        """Execute a tool call"""
        # 1. Try local skill
        local_tools = {t["function"]["name"] for t in self.skill_loader.get_all_tools()}
        if tool_name in local_tools:
            # Verify skill permission at call time too
            if context:
                skill_name = self.skill_loader._tool_to_skill.get(tool_name, "")
                allowed = getattr(context, "allowed_skills", None) or []
                if allowed and skill_name not in allowed and skill_name not in PLATFORM_SKILLS:
                    return json.dumps({"error": f"Skill '{skill_name}' not available for this tenant"}, ensure_ascii=False)
            return await self.skill_loader.execute_tool(tool_name, arguments)

        # 2. Try MCP
        if self.mcp_client:
            mcp_tools = {t["function"]["name"] for t in self.mcp_client.get_tools()}
            if tool_name in mcp_tools:
                return await self.mcp_client.call_tool(tool_name, arguments)

        return json.dumps({"error": f"Unknown tool: {tool_name}"}, ensure_ascii=False)
