"""
对话用例
"""
from typing import Optional
import uuid

from ...domain.entities.conversation import Conversation
from ...domain.entities.message import Message
from ...domain.services.conversation_service import ConversationService
from ...domain.services.tenant_service import TenantService
from ...domain.repositories.conversation_repository import IConversationRepository
from ...domain.repositories.message_repository import IMessageRepository
from ...infrastructure.external_services.dify_client import DifyClient

from ..dtos.chat_dto import ChatRequestDTO, ChatResponseDTO


class ChatUseCase:
    """对话用例"""
    
    def __init__(
        self,
        tenant_service: TenantService,
        conversation_service: ConversationService,
        dify_client: DifyClient
    ):
        self.tenant_service = tenant_service
        self.conversation_service = conversation_service
        self.dify_client = dify_client
    
    async def execute(self, tenant_id: str, request: ChatRequestDTO) -> ChatResponseDTO:
        """
        执行对话
        
        流程：
        1. 验证租户
        2. 获取或创建会话
        3. 保存用户消息
        4. 调用 Dify 获取回复
        5. 保存助手消息
        6. 返回响应
        """
        # 1. 验证租户
        tenant = await self.tenant_service.authenticate_by_id(tenant_id)
        if not tenant:
            raise ValueError("Tenant not found or inactive")
        
        # 2. 获取或创建会话
        session_id = request.session_id or f"sess_{uuid.uuid4().hex[:12]}"
        
        # 3. 保存用户消息
        user_message = await self.conversation_service.add_message(
            conversation_id=session_id,
            tenant_id=tenant_id,
            role="user",
            content=request.message,
            content_type="text",
            metadata=request.metadata
        )
        
        # 4. 调用 Dify
        try:
            dify_response = await self.dify_client.chat(
                query=request.message,
                conversation_id=session_id,
                user_id=request.user_id or "anonymous",
                inputs={}
            )
            
            reply = dify_response.get("answer", "")
            tokens_used = dify_response.get("metadata", {}).get("usage", {}).get("total_tokens", 0)
            
        except Exception as e:
            reply = f"抱歉，服务暂时不可用，请稍后重试。"
            tokens_used = 0
        
        # 5. 保存助手消息
        assistant_message = await self.conversation_service.add_message(
            conversation_id=session_id,
            tenant_id=tenant_id,
            role="assistant",
            content=reply,
            tokens_used=tokens_used,
            metadata={"source": "dify"}
        )
        
        # 6. 消耗配额
        await self.tenant_service.consume_quota(tenant_id, tokens_used)
        
        # 7. 返回响应
        return ChatResponseDTO(
            session_id=session_id,
            message_id=assistant_message.id,
            reply=reply,
            tokens_used=tokens_used
        )
    
    async def get_history(
        self,
        tenant_id: str,
        conversation_id: str,
        limit: int = 50
    ) -> list:
        """获取对话历史"""
        messages = await self.conversation_service.get_conversation_history(
            conversation_id=conversation_id,
            limit=limit
        )
        
        return [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat()
            }
            for msg in messages
        ]
