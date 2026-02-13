"""
Database engine and async session management.

Provides:
- Async SQLAlchemy engine
- Session factory
- FastAPI dependency for request-scoped sessions
- Declarative base for ORM models
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


# ---------------------------------------------------------------------------
# Engine and session factory (created once at module import)
# ---------------------------------------------------------------------------

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.app_debug,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

def get_db_session():
    """
    Async context manager for background tasks (not FastAPI dependency).

    Usage:
        async with get_db_session() as db:
            ...
            await db.commit()
    """
    return async_session_factory()


async def get_db() -> AsyncSession:
    """
    Yield a database session for a single request.
    Automatically commits on success, rolls back on exception.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
