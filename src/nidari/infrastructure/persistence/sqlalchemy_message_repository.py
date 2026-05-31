"""
SQLAlchemy message repository implementation
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ...domain.entities.message import Message
from ...domain.repositories.message_repository import IMessageRepository
from .models import MessageModel


class SQLAlchemyMessageRepository(IMessageRepository):
    """SQLAlchemy message repo"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, message_id: str) -> Optional[Message]:
        result = await self.session.execute(
            select(MessageModel).where(MessageModel.id == message_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def create(self, message: Message) -> Message:
        model = self._to_model(message)
        self.session.add(model)
        await self.session.flush()
        return message

    async def list_by_conversation(
        self,
        conversation_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Message]:
        result = await self.session.execute(
            select(MessageModel)
            .where(MessageModel.conversation_id == conversation_id)
            .order_by(MessageModel.created_at)
            .offset(skip)
            .limit(limit)
        )
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def count_by_conversation(self, conversation_id: str) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(MessageModel)
            .where(MessageModel.conversation_id == conversation_id)
        )
        return result.scalar()

    async def count_by_tenant(self, tenant_id: str) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(MessageModel)
            .where(MessageModel.tenant_id == tenant_id)
        )
        return result.scalar()

    def _to_entity(self, model: MessageModel) -> Message:
        return Message(
            id=model.id,
            conversation_id=model.conversation_id,
            tenant_id=model.tenant_id,
            role=model.role,
            name=model.name,
            content=model.content,
            content_type=model.content_type,
            tool_calls=model.tool_calls,
            tool_call_id=model.tool_call_id,
            tokens_used=model.tokens_used,
            skill_used=model.skill_used,
            metadata=model.meta_data or {},
            created_at=model.created_at,
        )

    def _to_model(self, entity: Message) -> MessageModel:
        return MessageModel(
            id=entity.id,
            conversation_id=entity.conversation_id,
            tenant_id=entity.tenant_id,
            role=entity.role,
            name=entity.name,
            content=entity.content,
            content_type=entity.content_type,
            tool_calls=entity.tool_calls,
            tool_call_id=entity.tool_call_id,
            tokens_used=entity.tokens_used,
            skill_used=entity.skill_used,
            meta_data=entity.metadata,
            created_at=entity.created_at,
        )
