"""
Tool gateway adapter — with tenant skill isolation + role-based permission
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
    """Tool gateway with tenant skill isolation + role-based permission"""

    def __init__(self, skill_loader: SkillLoader, mcp_client: MCPClient = None,
                 role_repo_factory=None):
        self.skill_loader = skill_loader
        self.mcp_client = mcp_client
        self.role_repo_factory = role_repo_factory  # callable → AsyncSession → RoleRepository

    def set_role_repo_factory(self, factory):
        """注入角色仓储工厂（延迟注入）"""
        self.role_repo_factory = factory

    async def _with_role_repo(self, fn):
        """用临时 session 执行 role_repo 操作"""
        if not self.role_repo_factory:
            return None
        from ...infrastructure.persistence.database import async_session_factory
        from ...infrastructure.persistence.repositories.role_repo import RoleRepository
        async with async_session_factory() as session:
            repo = RoleRepository(session)
            result = await fn(repo)
            await session.commit()
            return result

    async def list_tools(self, context: TenantContext) -> List[Dict[str, Any]]:
        """
        Return tools available to this tenant + user.
        If role_repo_factory is available, use permission-aware filtering.
        """
        tenant = getattr(context, '_tenant_entity', None) if context else None

        # 新模式：基于角色的权限过滤
        if self.role_repo_factory and context and tenant:
            user_id = context.user_id
            role_name = context.metadata.get("role_name") if context.metadata else None

            async def _get_tools(repo):
                return await self.skill_loader.get_tools_for_user(
                    tenant, user_id, repo, role_name
                )
            tools = await self._with_role_repo(_get_tools)
            if tools is not None:
                if self.mcp_client:
                    tools.extend(self.mcp_client.get_tools())
                return tools

        # 兼容旧模式：按 allowed_skills 过滤
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
        """Execute a tool call with permission check"""
        # 1. Try local skill
        local_tools = {t["function"]["name"] for t in self.skill_loader.get_all_tools()}
        if tool_name in local_tools:
            tenant = getattr(context, '_tenant_entity', None) if context else None

            # Permission check via role_repo
            if self.role_repo_factory and context and tenant:
                skill_name = self.skill_loader._tool_to_skill.get(tool_name, "")
                if skill_name not in PLATFORM_SKILLS:
                    # 旧模式兼容检查
                    allowed = getattr(context, "allowed_skills", None) or []
                    if allowed and skill_name not in allowed:
                        return json.dumps(
                            {"error": f"Skill '{skill_name}' not available for this tenant"},
                            ensure_ascii=False
                        )

                    # 角色权限校验
                    async def _check(repo):
                        await self.skill_loader._assert_tool_access(
                            tenant, context.user_id, repo, skill_name, tool_name
                        )
                    try:
                        await self._with_role_repo(_check)
                    except PermissionError as e:
                        return json.dumps({"error": str(e)}, ensure_ascii=False)

            # 执行工具（无权限校验，上面已校验）
            return await self.skill_loader.execute_tool(tool_name, arguments)

        # 2. Try MCP
        if self.mcp_client:
            mcp_tools = {t["function"]["name"] for t in self.mcp_client.get_tools()}
            if tool_name in mcp_tools:
                return await self.mcp_client.call_tool(tool_name, arguments)

        return json.dumps({"error": f"Unknown tool: {tool_name}"}, ensure_ascii=False)
