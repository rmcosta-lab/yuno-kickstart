from __future__ import annotations

import asyncio
import os
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import create_async_engine

ROOT = Path(__file__).parents[4]


class _RedactedDatabaseUrl(str):
    def __repr__(self) -> str:
        return "<isolated PostgreSQL URL redacted>"


def _render_url(url: URL) -> str:
    return url.render_as_string(hide_password=False)


async def _create_database(admin_url: str, database_name: str) -> None:
    engine = create_async_engine(
        admin_url,
        isolation_level="AUTOCOMMIT",
        hide_parameters=True,
    )
    try:
        async with engine.connect() as connection:
            await connection.execute(text(f'CREATE DATABASE "{database_name}"'))
    finally:
        await engine.dispose()


async def _drop_database(admin_url: str, database_name: str) -> None:
    engine = create_async_engine(
        admin_url,
        isolation_level="AUTOCOMMIT",
        hide_parameters=True,
    )
    try:
        async with engine.connect() as connection:
            await connection.execute(text(f'DROP DATABASE "{database_name}" WITH (FORCE)'))
    finally:
        await engine.dispose()


@pytest.fixture(scope="session")
def isolated_database_url() -> Iterator[str]:
    configured_url = os.environ.get("TEST_DATABASE_URL")
    if not configured_url:
        pytest.skip("TEST_DATABASE_URL is required for isolated PostgreSQL tests")
    parsed = make_url(configured_url)
    if parsed.drivername != "postgresql+asyncpg":
        pytest.skip("isolated PostgreSQL URL must use asyncpg")
    if parsed.host not in {"localhost", "127.0.0.1", "::1"}:
        pytest.skip("isolated PostgreSQL tests require an explicit loopback host")

    database_name = f"volta_phase6_{uuid4().hex}"
    test_url = parsed.set(database=database_name)
    rendered_admin_url = _render_url(parsed)
    rendered_test_url = _render_url(test_url)
    asyncio.run(_create_database(rendered_admin_url, database_name))

    previous_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = rendered_test_url
    alembic_config = Config(str(ROOT / "backend" / "alembic.ini"))
    try:
        command.upgrade(alembic_config, "head")
        yield _RedactedDatabaseUrl(rendered_test_url)
    finally:
        try:
            try:
                command.downgrade(alembic_config, "base")
            except RuntimeError as error:
                if not any(
                    marker in str(error)
                    for marker in (
                        "phase 25 downgrade refused",
                        "phase 27 downgrade refused",
                        "phase 28 downgrade refused",
                    )
                ):
                    raise
        finally:
            if previous_url is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = previous_url
            asyncio.run(_drop_database(rendered_admin_url, database_name))


@pytest.fixture
def alembic_config(isolated_database_url: str) -> Config:
    return Config(str(ROOT / "backend" / "alembic.ini"))
