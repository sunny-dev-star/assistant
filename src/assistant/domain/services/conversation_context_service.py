"""
会话上下文构建与管理服务 (Domain Service)
"""
from typing import List, Dict, Any

from ..models.context import TenantContext
from ..entities.message import Message


class ConversationContextService:
    """会话上下文管理领域服务"""
    
    def build_context_messages(
        self,
        context: TenantContext,
        history: List[Message],
        system_prompt: str = ""
    ) -> List[Dict[str, Any]]:
        """
        根据历史消息构建大模型可理解的 messages 列表
        支持滑动窗口(简易版)和组装群聊发言人等特性
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
            
        # 简易 Token / 轮次裁剪策略：保留最后 20 条消息
        history_to_keep = history[-20:]
        
        for msg in history_to_keep:
            # 群聊/多用户场景，使用 name 字段
            m = {
                "role": msg.role,
                "content": msg.content
            }
            if msg.name:
                m["name"] = msg.name
                
            if msg.role == "assistant" and msg.tool_calls:
                m["tool_calls"] = msg.tool_calls
            elif msg.role == "tool" and msg.tool_call_id:
                m["tool_call_id"] = msg.tool_call_id
                
            messages.append(m)
            
        return messages

    def append_user_message(
        self,
        context: TenantContext,
        history: List[Message],
        content: str,
        user_name: str = None
    ) -> Message:
        """
        追加用户消息并返回实体
        """
        msg = Message.create_user_message(
            conversation_id=context.session_id,
            tenant_id=context.tenant_id,
            content=content,
            name=user_name
        )
        history.append(msg)
        return msg
