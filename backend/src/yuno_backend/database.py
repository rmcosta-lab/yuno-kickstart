"""SQLAlchemy configuration without transport or application-framework coupling."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for future persistence models."""


@dataclass(frozen=True, slots=True)
class DatabaseConfig:
    """Settings required to construct an asynchronous PostgreSQL engine."""

    url: str = field(repr=False)
    echo: bool = False
    pool_pre_ping: bool = True

    def __post_init__(self) -> None:
        if not self.url.startswith("postgresql+asyncpg://"):
            message = "DATABASE_URL must use the postgresql+asyncpg driver"
            raise ValueError(message)

    @classmethod
    def from_environment(
        cls,
        environ: Mapping[str, str] | None = None,
    ) -> DatabaseConfig:
        values = os.environ if environ is None else environ
        database_url = values.get("DATABASE_URL")
        if not database_url:
            message = "DATABASE_URL is required"
            raise RuntimeError(message)
        return cls(url=database_url)


def create_database_engine(config: DatabaseConfig) -> AsyncEngine:
    """Create a lazy async engine; no connection is opened by this function."""

    return create_async_engine(
        config.url,
        echo=config.echo,
        pool_pre_ping=config.pool_pre_ping,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create sessions whose loaded state remains available after commit."""

    return async_sessionmaker(engine, expire_on_commit=False)


async def session_scope(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Yield one session and guarantee that it is closed afterwards."""

    async with session_factory() as session:
        yield session
