"""
会话仓储接口
"""
from abc import ABC, abstractmethod
from typing import Optional, List

from ..entities.conversation import Conversation


class IConversationRepository(ABC):
    """会话仓储接口"""
    
    @abstractmethod
    async def get_by_id(self, conversation_id: str) -> Optional[Conversation]:
        """根据 ID 获取会话"""
        pass
    
    @abstractmethod
    async def create(self, conversation: Conversation) -> Conversation:
        """创建会话"""
        pass
    
    @abstractmethod
    async def update(self, conversation: Conversation) -> Conversation:
        """更新会话"""
        pass
    
    @abstractmethod
    async def delete(self, conversation_id: str) -> bool:
        """删除会话"""
        pass
    
    @abstractmethod
    async def list_by_tenant(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Conversation]:
        """列出租户的所有会话"""
        pass
    
    @abstractmethod
    async def list_by_user(
        self,
        tenant_id: str,
        user_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Conversation]:
        """列出用户的所有会话"""
        pass
    
    @abstractmethod
    async def count_by_tenant(self, tenant_id: str) -> int:
        """统计租户的会话数量"""
        pass
