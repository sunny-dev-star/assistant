"""
Database-backed message repository proxy.
Creates a fresh DB session per operation to ensure proper transaction isolation.
"""
from typing import Optional, List
from ...domain.entities.message import Message
from ...domain.repositories.message_repository import IMessageRepository
from .database import async_session_factory
from .sqlalchemy_message_repository import SQLAlchemyMessageRepository


class DatabaseMessageRepository(IMessageRepository):
    """
    Proxy that creates a new DB session per operation.
    Used as the singleton in app.state, but each call gets its own session.
    """

    async def get_by_id(self, message_id: str) -> Optional[Message]:
        async with async_session_factory() as session:
            repo = SQLAlchemyMessageRepository(session)
            return await repo.get_by_id(message_id)

    async def create(self, message: Message) -> Message:
        async with async_session_factory() as session:
            repo = SQLAlchemyMessageRepository(session)
            result = await repo.create(message)
            await session.commit()
            return result

    async def list_by_conversation(
        self,
        conversation_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Message]:
        async with async_session_factory() as session:
            repo = SQLAlchemyMessageRepository(session)
            return await repo.list_by_conversation(conversation_id, skip, limit)

    async def count_by_conversation(self, conversation_id: str) -> int:
        async with async_session_factory() as session:
            repo = SQLAlchemyMessageRepository(session)
            return await repo.count_by_conversation(conversation_id)

    async def count_by_tenant(self, tenant_id: str) -> int:
        async with async_session_factory() as session:
            repo = SQLAlchemyMessageRepository(session)
            return await repo.count_by_tenant(tenant_id)
