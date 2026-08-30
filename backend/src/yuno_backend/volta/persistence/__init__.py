"""Public SQLAlchemy persistence adapters for the Volta application core."""

from yuno_backend.volta.persistence.errors import PersistenceConflict, PersistenceUnavailable
from yuno_backend.volta.persistence.repositories import (
    SqlAlchemyAuditEventRepository,
    SqlAlchemyBriefRepository,
    SqlAlchemyCommitmentRepository,
    SqlAlchemyEvidenceRepository,
    SqlAlchemyIdempotencyRepository,
    SqlAlchemyIntakeDraftRepository,
    SqlAlchemyNegotiationRepository,
    SqlAlchemyNotificationRepository,
    SqlAlchemyOperationRepository,
    SqlAlchemyPostContactEscalationRepository,
    SqlAlchemyQuoteRepository,
    SqlAlchemyRecapRepository,
    SqlAlchemyRecoveryAttemptRepository,
)
from yuno_backend.volta.persistence.unit_of_work import SqlAlchemyOperationUnitOfWork

__all__ = [
    "PersistenceConflict",
    "PersistenceUnavailable",
    "SqlAlchemyAuditEventRepository",
    "SqlAlchemyBriefRepository",
    "SqlAlchemyCommitmentRepository",
    "SqlAlchemyEvidenceRepository",
    "SqlAlchemyIdempotencyRepository",
    "SqlAlchemyIntakeDraftRepository",
    "SqlAlchemyNegotiationRepository",
    "SqlAlchemyNotificationRepository",
    "SqlAlchemyOperationRepository",
    "SqlAlchemyOperationUnitOfWork",
    "SqlAlchemyPostContactEscalationRepository",
    "SqlAlchemyQuoteRepository",
    "SqlAlchemyRecapRepository",
    "SqlAlchemyRecoveryAttemptRepository",
]
