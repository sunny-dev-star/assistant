"""
内存消息仓储实现 (用于 MVP 和测试)
"""
from typing import Optional, List, Dict

from ...domain.entities.message import Message
from ...domain.repositories.message_repository import IMessageRepository


class MemoryMessageRepository(IMessageRepository):
    """内存消息仓储"""
    
    def __init__(self):
        self._messages: Dict[str, Message] = {}
        
    async def get_by_id(self, message_id: str) -> Optional[Message]:
        return self._messages.get(message_id)
        
    async def create(self, message: Message) -> Message:
        self._messages[message.id] = message
        return message
        
    async def list_by_conversation(
        self,
        conversation_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Message]:
        msgs = [m for m in self._messages.values() if m.conversation_id == conversation_id]
        # 根据 created_at 排序
        msgs.sort(key=lambda x: x.created_at)
        return msgs[skip : skip + limit]
        
    async def count_by_conversation(self, conversation_id: str) -> int:
        return sum(1 for m in self._messages.values() if m.conversation_id == conversation_id)
        
    async def count_by_tenant(self, tenant_id: str) -> int:
        return sum(1 for m in self._messages.values() if m.tenant_id == tenant_id)
