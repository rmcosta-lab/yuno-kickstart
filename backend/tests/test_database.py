from __future__ import annotations

import pytest
from yuno_backend.database import (
    DatabaseConfig,
    create_database_engine,
    create_session_factory,
    normalize_database_url,
)


@pytest.mark.parametrize("scheme", ["postgresql://", "postgres://"])
def test_database_config_adapts_standard_provider_urls(scheme: str) -> None:
    config = DatabaseConfig(url=f"{scheme}user:secret@localhost/yuno")

    assert config.url == "postgresql+asyncpg://user:secret@localhost/yuno"


def test_database_config_rejects_non_postgresql_urls() -> None:
    with pytest.raises(ValueError, match="PostgreSQL URL"):
        normalize_database_url("sqlite:///tmp/yuno.db")


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
