"""
会话领域服务
处理会话相关的核心业务逻辑
"""
from typing import Optional, List

from ..entities.conversation import Conversation
from ..entities.message import Message
from ..repositories.conversation_repository import IConversationRepository
from ..repositories.message_repository import IMessageRepository


class ConversationService:
    """会话领域服务"""
    
    def __init__(
        self,
        conversation_repo: IConversationRepository,
        message_repo: IMessageRepository
    ):
        self.conversation_repo = conversation_repo
        self.message_repo = message_repo
    
    async def create_conversation(
        self,
        tenant_id: str,
        user_id: str,
        channel: str
    ) -> Conversation:
        """创建新会话"""
        conversation = Conversation(
            tenant_id=tenant_id,
            user_id=user_id,
            channel=channel
        )
        return await self.conversation_repo.create(conversation)
    
    async def add_message(
        self,
        conversation_id: str,
        tenant_id: str,
        role: str,
        content: str,
        content_type: str = "text",
        tokens_used: int = 0,
        skill_used: Optional[str] = None,
        metadata: dict = None
    ) -> Message:
        """添加消息到会话"""
        if role == "user":
            message = Message.create_user_message(
                conversation_id=conversation_id,
                tenant_id=tenant_id,
                content=content,
                content_type=content_type,
                metadata=metadata or {}
            )
        else:
            message = Message.create_assistant_message(
                conversation_id=conversation_id,
                tenant_id=tenant_id,
                content=content,
                tokens_used=tokens_used,
                skill_used=skill_used,
                metadata=metadata or {}
            )
        
        return await self.message_repo.create(message)
    
    async def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 50
    ) -> List[Message]:
        """获取会话历史"""
        return await self.message_repo.list_by_conversation(
            conversation_id,
            limit=limit
        )
    
    async def close_conversation(self, conversation_id: str) -> bool:
        """关闭会话"""
        conversation = await self.conversation_repo.get_by_id(conversation_id)
        if not conversation:
            return False
        
        conversation.close()
        await self.conversation_repo.update(conversation)
        return True
    
    async def get_user_conversations(
        self,
        tenant_id: str,
        user_id: str,
        limit: int = 20
    ) -> List[Conversation]:
        """获取用户的会话列表"""
        return await self.conversation_repo.list_by_user(
            tenant_id=tenant_id,
            user_id=user_id,
            limit=limit
        )
