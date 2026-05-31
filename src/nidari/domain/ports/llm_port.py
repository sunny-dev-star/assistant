"""
大模型调用出站端口 (LLM Outbound Port)
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from ..models.context import TenantContext


@dataclass
class LLMResponse:
    """大模型统一响应"""
    content: str = ""
    tool_calls: Optional[List[Dict[str, Any]]] = None
    
    # Token 统计与计费
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0


class ILLMChatPort(ABC):
    """大模型聊天端口"""
    
    @abstractmethod
    async def chat(
        self,
        context: TenantContext,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = "auto"
    ) -> LLMResponse:
        """
        发起大模型对话请求
        """
        pass
