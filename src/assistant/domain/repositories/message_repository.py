"""
消息仓储接口
"""
from abc import ABC, abstractmethod
from typing import Optional, List

from ..entities.message import Message


class IMessageRepository(ABC):
    """消息仓储接口"""
    
    @abstractmethod
    async def get_by_id(self, message_id: str) -> Optional[Message]:
        """根据 ID 获取消息"""
        pass
    
    @abstractmethod
    async def create(self, message: Message) -> Message:
        """创建消息"""
        pass
    
    @abstractmethod
    async def list_by_conversation(
        self,
        conversation_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Message]:
        """列出会话的所有消息"""
        pass
    
    @abstractmethod
    async def count_by_conversation(self, conversation_id: str) -> int:
        """统计会话的消息数量"""
        pass
    
    @abstractmethod
    async def count_by_tenant(self, tenant_id: str) -> int:
        """统计租户的消息数量"""
        pass
