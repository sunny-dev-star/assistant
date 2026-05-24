"""
Database engine & session management
Supports SQLite (dev) and PostgreSQL (prod)
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator

from ...infrastructure.config.settings import settings


def _build_engine():
    url = settings.DATABASE_URL
    if url.startswith("sqlite"):
        # SQLite: no pool, enable check_same_thread
        return create_async_engine(url, echo=settings.DEBUG)
    else:
        # PostgreSQL
        return create_async_engine(
            url,
            pool_size=settings.DATABASE_POOL_SIZE,
            echo=settings.DEBUG,
        )


engine = _build_engine()
async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    """ORM base class"""
    pass


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a DB session for FastAPI DI"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Create all tables"""
    from . import models  # noqa: F401 - ensure models are registered
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
