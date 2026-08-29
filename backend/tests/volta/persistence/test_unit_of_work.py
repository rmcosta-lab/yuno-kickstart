from uuid import UUID

import pytest
from sqlalchemy.exc import DBAPIError
from yuno_backend.volta.persistence import (
    PersistenceConflict,
    PersistenceUnavailable,
    SqlAlchemyOperationUnitOfWork,
)


def test_persistence_errors_accept_only_stable_safe_codes_and_uuid_identifiers() -> None:
    error = PersistenceConflict("integrity_constraint", "operation", UUID(int=1))
    assert error.reason_code == "integrity_constraint"
    assert "SELECT" not in str(error)

    with pytest.raises(ValueError, match="stable safe codes"):
        PersistenceUnavailable("SELECT source_prompt", "operation")
    with pytest.raises(TypeError, match="UUID"):
        PersistenceUnavailable("read_failed", "operation", "submitted")  # type: ignore[arg-type]


async def test_begin_failure_closes_session_resets_uow_and_translates_safely() -> None:
    class FailingSession:
        closed = False

        async def begin(self) -> None:
            raise DBAPIError("BEGIN secret", {"prompt": "hidden"}, RuntimeError("driver secret"))

        async def close(self) -> None:
            self.closed = True

    session = FailingSession()
    uow = SqlAlchemyOperationUnitOfWork(lambda: session)  # type: ignore[arg-type]

    with pytest.raises(PersistenceUnavailable) as captured:
        await uow.__aenter__()

    assert session.closed
    assert "secret" not in str(captured.value)
    assert not hasattr(uow, "operations")
