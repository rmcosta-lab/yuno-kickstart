"""Short-lived SQLAlchemy session and transaction ownership for one operation."""

from types import TracebackType

from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from yuno_backend.volta.persistence.errors import PersistenceConflict, PersistenceUnavailable
from yuno_backend.volta.persistence.repositories import (
    SqlAlchemyAuditEventRepository,
    SqlAlchemyIntakeDraftRepository,
    SqlAlchemyOperationRepository,
)

__all__ = ["SqlAlchemyOperationUnitOfWork"]


class SqlAlchemyOperationUnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self.intake_drafts: SqlAlchemyIntakeDraftRepository
        self.operations: SqlAlchemyOperationRepository
        self.audit_events: SqlAlchemyAuditEventRepository

    async def __aenter__(self) -> "SqlAlchemyOperationUnitOfWork":
        if self._session is not None:
            raise RuntimeError("unit of work is already active")
        self._session = self._session_factory()
        try:
            await self._session.begin()
        except DBAPIError:
            await self._session.close()
            self._session = None
            raise PersistenceUnavailable("begin_failed", "unit_of_work") from None
        self.intake_drafts = SqlAlchemyIntakeDraftRepository(self._session)
        self.operations = SqlAlchemyOperationRepository(self._session)
        self.audit_events = SqlAlchemyAuditEventRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        session = self._require_session()
        try:
            if session.in_transaction():
                await session.rollback()
        finally:
            await session.close()
            self._session = None
            del self.intake_drafts
            del self.operations
            del self.audit_events

    async def commit(self) -> None:
        session = self._require_session()
        try:
            await session.commit()
        except IntegrityError:
            raise PersistenceConflict("integrity_constraint", "unit_of_work") from None
        except DBAPIError:
            raise PersistenceUnavailable("commit_failed", "unit_of_work") from None

    async def rollback(self) -> None:
        session = self._require_session()
        try:
            if session.in_transaction():
                await session.rollback()
        except DBAPIError:
            raise PersistenceUnavailable("rollback_failed", "unit_of_work") from None

    def _require_session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("unit of work is not active")
        return self._session
