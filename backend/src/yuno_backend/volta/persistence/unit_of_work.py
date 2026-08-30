"""Short-lived SQLAlchemy session and transaction ownership for one operation."""

from types import TracebackType

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from yuno_backend.volta.persistence.errors import PersistenceConflict, PersistenceUnavailable
from yuno_backend.volta.persistence.repositories import (
    SqlAlchemyAuditEventRepository,
    SqlAlchemyBriefRepository,
    SqlAlchemyCommitmentRepository,
    SqlAlchemyEvidenceRepository,
    SqlAlchemyEvidenceReservationRepository,
    SqlAlchemyIdempotencyRepository,
    SqlAlchemyIntakeDraftRepository,
    SqlAlchemyNegotiationRepository,
    SqlAlchemyNotificationRepository,
    SqlAlchemyOperationRepository,
    SqlAlchemyPostContactEscalationRepository,
    SqlAlchemyQuoteRepository,
    SqlAlchemyRecapRepository,
    SqlAlchemyRecoveryAttemptRepository,
    SqlAlchemyTextMutationIdempotencyRepository,
)

__all__ = ["SqlAlchemyOperationUnitOfWork"]


class SqlAlchemyOperationUnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self.intake_drafts: SqlAlchemyIntakeDraftRepository
        self.operations: SqlAlchemyOperationRepository
        self.audit_events: SqlAlchemyAuditEventRepository
        self.negotiations: SqlAlchemyNegotiationRepository
        self.quotes: SqlAlchemyQuoteRepository
        self.commitments: SqlAlchemyCommitmentRepository
        self.idempotency: SqlAlchemyIdempotencyRepository
        self.evidence: SqlAlchemyEvidenceRepository
        self.evidence_reservations: SqlAlchemyEvidenceReservationRepository
        self.briefs: SqlAlchemyBriefRepository
        self.recaps: SqlAlchemyRecapRepository
        self.recovery_attempts: SqlAlchemyRecoveryAttemptRepository
        self.post_contact_escalations: SqlAlchemyPostContactEscalationRepository
        self.notifications: SqlAlchemyNotificationRepository
        self.text_idempotency: SqlAlchemyTextMutationIdempotencyRepository

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
        self.negotiations = SqlAlchemyNegotiationRepository(self._session)
        self.quotes = SqlAlchemyQuoteRepository(self._session)
        self.commitments = SqlAlchemyCommitmentRepository(self._session)
        self.idempotency = SqlAlchemyIdempotencyRepository(self._session)
        self.evidence = SqlAlchemyEvidenceRepository(self._session)
        self.evidence_reservations = SqlAlchemyEvidenceReservationRepository(self._session)
        self.briefs = SqlAlchemyBriefRepository(self._session)
        self.recaps = SqlAlchemyRecapRepository(self._session)
        self.recovery_attempts = SqlAlchemyRecoveryAttemptRepository(self._session)
        self.post_contact_escalations = SqlAlchemyPostContactEscalationRepository(self._session)
        self.notifications = SqlAlchemyNotificationRepository(self._session)
        self.text_idempotency = SqlAlchemyTextMutationIdempotencyRepository(self._session)
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
            del self.negotiations
            del self.quotes
            del self.commitments
            del self.idempotency
            del self.evidence
            del self.evidence_reservations
            del self.briefs
            del self.recaps
            del self.recovery_attempts
            del self.post_contact_escalations
            del self.notifications
            del self.text_idempotency

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

    async def stabilize_read_snapshot(self) -> None:
        """Pin subsequent reads to one PostgreSQL MVCC snapshot."""
        session = self._require_session()
        try:
            await session.execute(
                text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            )
        except DBAPIError:
            raise PersistenceUnavailable(
                "snapshot_failed", "unit_of_work"
            ) from None

    def _require_session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("unit of work is not active")
        return self._session
