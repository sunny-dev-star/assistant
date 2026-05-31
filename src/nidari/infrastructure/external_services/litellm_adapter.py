"""
LiteLLM 适配器
统一接入各厂商大模型并计算计费 Token
"""
import os
import litellm
from typing import Dict, Any, List, Optional
import logging

from ...domain.ports.llm_port import ILLMChatPort, LLMResponse
from ...domain.models.context import TenantContext

logger = logging.getLogger(__name__)

class LiteLLMAdapter(ILLMChatPort):
    """LiteLLM 适配器实现"""

    async def chat(
        self,
        context: TenantContext,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = "auto"
    ) -> LLMResponse:
        """
        调用大模型
        """
        config = context.llm_config
        model_name = config.model
        
        # 组装参数
        kwargs = {
            "model": model_name,
            "messages": messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "user": context.user_id, # LiteLLM 会记录用户追踪
        }

        if config.api_key:
            kwargs["api_key"] = config.api_key
        if config.api_base:
            kwargs["api_base"] = config.api_base
            
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice

        logger.info(f"Calling LLM: {model_name} for tenant: {context.tenant_id}")
        try:
            response = await litellm.acompletion(**kwargs)
            
            choice = response.choices[0]
            message = choice.message
            
            content = message.content or ""
            
            tool_calls = None
            if hasattr(message, "tool_calls") and message.tool_calls:
                tool_calls = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in message.tool_calls
                ]

            usage = response.usage
            prompt_tokens = usage.prompt_tokens if usage else 0
            completion_tokens = usage.completion_tokens if usage else 0
            total_tokens = usage.total_tokens if usage else 0
            
            # 使用 litellm 计算成本
            cost_usd = 0.0
            try:
                cost_usd = litellm.completion_cost(completion_response=response)
            except Exception as e:
                logger.warning(f"Failed to calculate cost for model {model_name}: {e}")

            return LLMResponse(
                content=content,
                tool_calls=tool_calls,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_usd=cost_usd
            )
            
        except Exception as e:
            logger.error(f"LiteLLM call failed: {e}")
            raise
