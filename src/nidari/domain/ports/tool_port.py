"""
工具网关出站端口 (Tool Gateway Outbound Port)
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List

from ..models.context import TenantContext


class IToolGateway(ABC):
    """工具与技能调用网关"""
    
    @abstractmethod
    async def list_tools(
        self,
        context: TenantContext
    ) -> List[Dict[str, Any]]:
        """
        获取当前上下文(租户/用户)可用的工具列表
        (格式符合 OpenAI Tools Schema)
        """
        pass

    @abstractmethod
    async def call_tool(
        self,
        context: TenantContext,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> str:
        """
        执行工具调用，返回结果字符串
        """
        pass
