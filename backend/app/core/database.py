"""Database configuration and session management."""

import os
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker, AsyncEngine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


def _get_async_url() -> str:
    """Get the async database URL, converting from standard format if needed."""
    url = os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/mias_reminder")
    # Railway/Heroku give postgresql:// or postgres:// — convert to asyncpg
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


# Lazy engine and session — created on first use
_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker] = None


def get_engine() -> AsyncEngine:
    """Get or create the async engine."""
    global _engine
    if _engine is None:
        debug = os.environ.get("DEBUG", "false").lower() == "true"
        _engine = create_async_engine(
            _get_async_url(),
            echo=debug,
            pool_size=20,
            max_overflow=10,
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory() -> async_sessionmaker:
    """Get or create the session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def get_db() -> AsyncSession:
    """Dependency to get database session."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections."""
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None
