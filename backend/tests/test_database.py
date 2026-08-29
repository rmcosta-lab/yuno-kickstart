from __future__ import annotations

import pytest
from yuno_backend.database import (
    DatabaseConfig,
    create_database_engine,
    create_session_factory,
)


def test_database_config_requires_asyncpg_url() -> None:
    with pytest.raises(ValueError, match=r"postgresql\+asyncpg"):
        DatabaseConfig(url="postgresql://localhost/yuno")


def test_database_config_reads_environment_without_exposing_url() -> None:
    config = DatabaseConfig.from_environment(
        {"DATABASE_URL": "postgresql+asyncpg://user:secret@localhost/yuno"}
    )

    assert "secret" not in repr(config)


async def test_engine_and_session_factory_are_lazy() -> None:
    config = DatabaseConfig(url="postgresql+asyncpg://user:secret@localhost/yuno")
    engine = create_database_engine(config)
    session_factory = create_session_factory(engine)

    assert engine.url.drivername == "postgresql+asyncpg"
    assert session_factory.kw["expire_on_commit"] is False

    await engine.dispose()
