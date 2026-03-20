from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# ─── Engine ───────────────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

# ─── Session factory ──────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ─── Base class ───────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ─── FastAPI dependency ───────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
