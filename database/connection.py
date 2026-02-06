from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import os


class Base(DeclarativeBase):
    pass


_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        database_url = os.getenv(
            "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/builder_curation"
        )
        _engine = create_async_engine(database_url, echo=False)
    return _engine


def get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def init_db():
    from .models import Base

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
