"""Async SQLAlchemy repositories returning only frozen provider-neutral values."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import insert, select, text, tuple_, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from yuno_backend.volta.audit.models import AuditEvent
from yuno_backend.volta.evidence.models import AgreementEvidence, CallBrief, Recap
from yuno_backend.volta.idempotency import TextMutationIdempotency
from yuno_backend.volta.mandates.errors import InvalidDomainValue, OperationAlreadyApproved
from yuno_backend.volta.mandates.models import IntakeDraft, Operation
from yuno_backend.volta.negotiations.models import (
    Commitment,
    MutationIdempotency,
    Negotiation,
    Quote,
)
from yuno_backend.volta.persistence.errors import PersistenceConflict, PersistenceUnavailable
from yuno_backend.volta.persistence.mappers import (
    _audit_from_row,
    _audit_to_values,
    _brief_from_row,
    _brief_to_values,
    _commitment_from_row,
    _commitment_to_values,
    _draft_from_row,
    _draft_to_values,
    _escalation_to_values,
    _evidence_from_row,
    _evidence_to_values,
    _idempotency_from_row,
    _idempotency_to_values,
    _mandate_to_values,
    _negotiation_from_rows,
    _notification_from_row,
    _notification_to_values,
    _operation_from_rows,
    _operation_to_values,
    _post_contact_escalation_from_row,
    _post_contact_escalation_to_values,
    _quote_from_row,
    _quote_to_values,
    _recap_from_row,
    _recap_to_values,
    _recovery_attempt_from_row,
    _recovery_attempt_to_values,
    _session_to_values,
    _status_to_values,
    _text_idempotency_from_row,
    _text_idempotency_to_values,
)
from yuno_backend.volta.persistence.tables import (
    _agreement_evidence,
    _audit_events,
    _call_briefs,
    _carrier_sessions,
    _commitments,
    _evidence_reservations,
    _intake_drafts,
    _mandates,
    _mutation_idempotency,
    _negotiations,
    _notifications,
    _operation_status_history,
    _operations,
    _post_contact_escalations,
    _pre_contact_escalations,
    _quotes,
    _recaps,
    _recovery_attempts,
    _text_mutation_idempotency,
)
from yuno_backend.volta.recovery.models import Notification, PostContactEscalation, RecoveryAttempt
from yuno_backend.volta.text_slice.models import EvidenceReservation

__all__ = [
    "SqlAlchemyAuditEventRepository",
    "SqlAlchemyBriefRepository",
    "SqlAlchemyCommitmentRepository",
    "SqlAlchemyEvidenceRepository",
    "SqlAlchemyEvidenceReservationRepository",
    "SqlAlchemyIdempotencyRepository",
    "SqlAlchemyIntakeDraftRepository",
    "SqlAlchemyNegotiationRepository",
    "SqlAlchemyNotificationRepository",
    "SqlAlchemyOperationRepository",
    "SqlAlchemyPostContactEscalationRepository",
    "SqlAlchemyQuoteRepository",
    "SqlAlchemyRecapRepository",
    "SqlAlchemyRecoveryAttemptRepository",
    "SqlAlchemyTextMutationIdempotencyRepository",
]


def _mapping(row: Any) -> Mapping[str, Any]:
    return row._mapping  # noqa: SLF001 - SQLAlchemy's documented Row mapping view


def _ordered_page(
    statement: Any,
    timestamp_column: Any,
    id_column: Any,
    *,
    after: tuple[datetime, UUID] | None,
    inclusive: bool,
    limit: int | None,
) -> Any:
    if after is not None:
        boundary = tuple_(timestamp_column, id_column)
        statement = statement.where(
            boundary >= after if inclusive else boundary > after
        )
    statement = statement.order_by(timestamp_column, id_column)
    return statement if limit is None else statement.limit(limit)


class SqlAlchemyIntakeDraftRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, draft_id: UUID) -> IntakeDraft | None:
        try:
            row = (
                await self._session.execute(
                    select(_intake_drafts).where(_intake_drafts.c.id == draft_id)
                )
            ).first()
        except DBAPIError:
            raise PersistenceUnavailable("read_failed", "intake_draft", draft_id) from None
        if row is None:
            return None
        try:
            return _draft_from_row(_mapping(row))
        except (InvalidDomainValue, KeyError, TypeError, ValueError):
            raise PersistenceUnavailable("invalid_stored_state", "intake_draft", draft_id) from None

    async def add(self, draft: IntakeDraft) -> None:
        try:
            await self._session.execute(insert(_intake_drafts).values(_draft_to_values(draft)))
        except IntegrityError:
            raise PersistenceConflict("integrity_constraint", "intake_draft", draft.id) from None
        except DBAPIError:
            raise PersistenceUnavailable("write_failed", "intake_draft", draft.id) from None


class SqlAlchemyOperationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_draft_id(self, draft_id: UUID) -> Operation | None:
        return await self._get_by(_operations.c.source_draft_id == draft_id)

    async def get(self, operation_id: UUID, *, for_update: bool = False) -> Operation | None:
        return await self._get_by(_operations.c.id == operation_id, for_update=for_update)

    async def _get_by(self, criterion: Any, *, for_update: bool = False) -> Operation | None:
        try:
            statement = select(_operations).where(criterion)
            if for_update:
                statement = statement.with_for_update()
            operation_row = (await self._session.execute(statement)).first()
            if operation_row is None:
                return None
            operation = _mapping(operation_row)
            mandate_row = (
                await self._session.execute(
                    select(_mandates).where(
                        _mandates.c.operation_id == operation["id"],
                        _mandates.c.id == operation["active_mandate_id"],
                    )
                )
            ).first()
            status_rows = (
                await self._session.execute(
                    select(_operation_status_history)
                    .where(_operation_status_history.c.operation_id == operation["id"])
                    .order_by(
                        _operation_status_history.c.occurred_at,
                        _operation_status_history.c.id,
                    )
                    .limit(101)
                )
            ).all()
        except DBAPIError:
            raise PersistenceUnavailable("read_failed", "operation") from None
        operation_id = operation["id"]
        if mandate_row is None:
            raise PersistenceUnavailable(
                "invalid_stored_state", "operation", operation_id
            ) from None
        if len(status_rows) > 100:
            raise PersistenceUnavailable(
                "aggregate_overflow", "operation_status_history", operation_id
            ) from None
        try:
            return _operation_from_rows(
                operation,
                _mapping(mandate_row),
                (_mapping(row) for row in status_rows),
            )
        except (InvalidDomainValue, IndexError, KeyError, TypeError, ValueError):
            raise PersistenceUnavailable(
                "invalid_stored_state", "operation", operation_id
            ) from None

    async def add(self, operation: Operation) -> None:
        try:
            inserted_id = (
                await self._session.execute(
                    postgresql_insert(_operations)
                    .values(_operation_to_values(operation))
                    .on_conflict_do_nothing(constraint="uq_volta_operations_source_draft_id")
                    .returning(_operations.c.id)
                )
            ).scalar_one_or_none()
            if inserted_id is None:
                existing_id = (
                    await self._session.execute(
                        select(_operations.c.id).where(
                            _operations.c.source_draft_id == operation.source_draft_id
                        )
                    )
                ).scalar_one_or_none()
                if existing_id is None:
                    raise PersistenceConflict(
                        "duplicate_state_unavailable", "operation", operation.id
                    )
                raise OperationAlreadyApproved(operation.source_draft_id, existing_id)
            await self._session.execute(
                insert(_mandates).values(_mandate_to_values(operation.mandate))
            )
            await self._session.execute(
                insert(_operation_status_history),
                [_status_to_values(entry) for entry in operation.status_history],
            )
        except IntegrityError:
            raise PersistenceConflict("integrity_constraint", "operation", operation.id) from None
        except DBAPIError:
            raise PersistenceUnavailable("write_failed", "operation", operation.id) from None

    async def update(self, operation: Operation) -> None:
        try:
            changed = (
                await self._session.execute(
                    update(_operations)
                    .where(_operations.c.id == operation.id)
                    .values(version=operation.version)
                    .returning(_operations.c.id)
                )
            ).scalar_one_or_none()
            if changed is None:
                raise PersistenceConflict("missing_state", "operation", operation.id)
            await self._session.execute(
                insert(_operation_status_history).values(
                    _status_to_values(operation.status_history[-1])
                )
            )
        except IntegrityError:
            raise PersistenceConflict("integrity_constraint", "operation", operation.id) from None
        except DBAPIError:
            raise PersistenceUnavailable("write_failed", "operation", operation.id) from None

    async def replace_mandate(self, operation: Operation) -> None:
        try:
            await self._session.execute(
                insert(_mandates).values(_mandate_to_values(operation.mandate))
            )
            changed = (
                await self._session.execute(
                    update(_operations)
                    .where(_operations.c.id == operation.id)
                    .values(
                        version=operation.version,
                        active_mandate_id=operation.mandate.id,
                    )
                    .returning(_operations.c.id)
                )
            ).scalar_one_or_none()
            if changed is None:
                raise PersistenceConflict("missing_state", "operation", operation.id)
            await self._session.execute(
                insert(_operation_status_history).values(
                    _status_to_values(operation.status_history[-1])
                )
            )
        except IntegrityError:
            raise PersistenceConflict("integrity_constraint", "operation", operation.id) from None
        except DBAPIError:
            raise PersistenceUnavailable("write_failed", "operation", operation.id) from None


class SqlAlchemyAuditEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, event: AuditEvent) -> None:
        try:
            await self._session.execute(insert(_audit_events).values(_audit_to_values(event)))
        except IntegrityError:
            raise PersistenceConflict(
                "integrity_constraint", "audit_event", event.event_id
            ) from None
        except DBAPIError:
            raise PersistenceUnavailable("write_failed", "audit_event", event.event_id) from None

    async def list_by_operation(
        self,
        operation_id: UUID,
        *,
        after: tuple[datetime, UUID] | None = None,
        inclusive: bool = False,
        limit: int | None = None,
    ) -> tuple[AuditEvent, ...]:
        try:
            rows = (
                await self._session.execute(
                    _ordered_page(
                        select(_audit_events).where(
                            _audit_events.c.operation_id == operation_id
                        ),
                        _audit_events.c.occurred_at,
                        _audit_events.c.event_id,
                        after=after,
                        inclusive=inclusive,
                        limit=limit,
                    )
                )
            ).all()
        except DBAPIError:
            raise PersistenceUnavailable("read_failed", "audit_event", operation_id) from None
        try:
            return tuple(_audit_from_row(_mapping(row)) for row in rows)
        except (InvalidDomainValue, KeyError, TypeError, ValueError):
            raise PersistenceUnavailable(
                "invalid_stored_state", "audit_event", operation_id
            ) from None


class SqlAlchemyNegotiationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, negotiation_id: UUID) -> Negotiation | None:
        return await self._get_by(_negotiations.c.id == negotiation_id)

    async def get_by_operation(self, operation_id: UUID) -> Negotiation | None:
        return await self._get_by(_negotiations.c.operation_id == operation_id)

    async def get_by_call(self, call_id: UUID) -> Negotiation | None:
        try:
            negotiation_id = (
                await self._session.execute(
                    select(_carrier_sessions.c.negotiation_id).where(
                        _carrier_sessions.c.call_id == call_id
                    )
                )
            ).scalar_one_or_none()
        except DBAPIError:
            raise PersistenceUnavailable("read_failed", "carrier_session", call_id) from None
        return None if negotiation_id is None else await self.get(negotiation_id)

    async def _get_by(self, criterion: Any) -> Negotiation | None:
        try:
            row = (await self._session.execute(select(_negotiations).where(criterion))).first()
            if row is None:
                return None
            identity = _mapping(row)
            sessions = (
                await self._session.execute(
                    select(_carrier_sessions)
                    .where(_carrier_sessions.c.negotiation_id == identity["id"])
                    .order_by(_carrier_sessions.c.selection_rank, _carrier_sessions.c.carrier_id)
                )
            ).all()
            escalation = (
                await self._session.execute(
                    select(_pre_contact_escalations).where(
                        _pre_contact_escalations.c.negotiation_id == identity["id"]
                    )
                )
            ).first()
            return _negotiation_from_rows(
                identity,
                (_mapping(item) for item in sessions),
                None if escalation is None else _mapping(escalation),
            )
        except DBAPIError:
            raise PersistenceUnavailable("read_failed", "negotiation") from None
        except (InvalidDomainValue, KeyError, TypeError, ValueError):
            raise PersistenceUnavailable("invalid_stored_state", "negotiation") from None

    async def add(self, negotiation: Negotiation) -> None:
        try:
            await self._session.execute(
                insert(_negotiations).values(
                    id=negotiation.id,
                    operation_id=negotiation.operation_id,
                    operation_version=negotiation.operation_version,
                    mandate_version=negotiation.mandate_version,
                    started_at=negotiation.started_at,
                )
            )
            if negotiation.sessions:
                await self._session.execute(
                    insert(_carrier_sessions),
                    [_session_to_values(item) for item in negotiation.sessions],
                )
            if negotiation.pre_contact_escalation is not None:
                await self._session.execute(
                    insert(_pre_contact_escalations).values(
                        _escalation_to_values(negotiation.pre_contact_escalation)
                    )
                )
        except IntegrityError:
            raise PersistenceConflict(
                "integrity_constraint", "negotiation", negotiation.id
            ) from None
        except DBAPIError:
            raise PersistenceUnavailable("write_failed", "negotiation", negotiation.id) from None


class SqlAlchemyQuoteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, quote_id: UUID) -> Quote | None:
        try:
            row = (
                await self._session.execute(select(_quotes).where(_quotes.c.id == quote_id))
            ).first()
            return None if row is None else _quote_from_row(_mapping(row))
        except DBAPIError:
            raise PersistenceUnavailable("read_failed", "quote", quote_id) from None
        except (InvalidDomainValue, KeyError, TypeError, ValueError):
            raise PersistenceUnavailable("invalid_stored_state", "quote", quote_id) from None

    async def list_by_operation(
        self, operation_id: UUID, *, after: tuple[datetime, UUID] | None = None,
        inclusive: bool = False, limit: int | None = None
    ) -> tuple[Quote, ...]:
        try:
            rows = (
                await self._session.execute(
                    _ordered_page(
                        select(_quotes).where(_quotes.c.operation_id == operation_id),
                        _quotes.c.created_at,
                        _quotes.c.id,
                        after=after,
                        inclusive=inclusive,
                        limit=limit,
                    )
                )
            ).all()
            return tuple(_quote_from_row(_mapping(row)) for row in rows)
        except DBAPIError:
            raise PersistenceUnavailable("read_failed", "quote", operation_id) from None
        except (InvalidDomainValue, KeyError, TypeError, ValueError):
            raise PersistenceUnavailable("invalid_stored_state", "quote", operation_id) from None

    async def add(self, quote: Quote) -> None:
        try:
            await self._session.execute(insert(_quotes).values(_quote_to_values(quote)))
        except IntegrityError:
            raise PersistenceConflict("integrity_constraint", "quote", quote.id) from None
        except DBAPIError:
            raise PersistenceUnavailable("write_failed", "quote", quote.id) from None


class SqlAlchemyCommitmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, commitment_id: UUID) -> Commitment | None:
        return await self._get_by(_commitments.c.id == commitment_id)

    async def get_active(self, operation_id: UUID) -> Commitment | None:
        return await self._get_by(
            (_commitments.c.operation_id == operation_id) & (_commitments.c.disposition == "ACTIVE")
        )

    async def _get_by(self, criterion: Any) -> Commitment | None:
        try:
            row = (await self._session.execute(select(_commitments).where(criterion))).first()
            return None if row is None else _commitment_from_row(_mapping(row))
        except DBAPIError:
            raise PersistenceUnavailable("read_failed", "commitment") from None
        except (InvalidDomainValue, KeyError, TypeError, ValueError):
            raise PersistenceUnavailable("invalid_stored_state", "commitment") from None

    async def list_by_operation(
        self, operation_id: UUID, *, after: tuple[datetime, UUID] | None = None,
        inclusive: bool = False, limit: int | None = None
    ) -> tuple[Commitment, ...]:
        try:
            rows = (
                await self._session.execute(
                    _ordered_page(
                        select(_commitments).where(
                            _commitments.c.operation_id == operation_id
                        ),
                        _commitments.c.created_at,
                        _commitments.c.id,
                        after=after,
                        inclusive=inclusive,
                        limit=limit,
                    )
                )
            ).all()
            return tuple(_commitment_from_row(_mapping(row)) for row in rows)
        except DBAPIError:
            raise PersistenceUnavailable("read_failed", "commitment", operation_id) from None

    async def add(self, commitment: Commitment) -> None:
        try:
            await self._session.execute(
                insert(_commitments).values(_commitment_to_values(commitment))
            )
        except IntegrityError:
            raise PersistenceConflict("integrity_constraint", "commitment", commitment.id) from None
        except DBAPIError:
            raise PersistenceUnavailable("write_failed", "commitment", commitment.id) from None

    async def update(self, commitment: Commitment) -> None:
        try:
            changed = (
                await self._session.execute(
                    update(_commitments)
                    .where(_commitments.c.id == commitment.id)
                    .values(_commitment_to_values(commitment))
                    .returning(_commitments.c.id)
                )
            ).scalar_one_or_none()
            if changed is None:
                raise PersistenceConflict("missing_state", "commitment", commitment.id)
        except IntegrityError:
            raise PersistenceConflict("integrity_constraint", "commitment", commitment.id) from None
        except DBAPIError:
            raise PersistenceUnavailable("write_failed", "commitment", commitment.id) from None

    async def lock_winner_scope(self, operation_id: UUID) -> None:
        try:
            await self._session.execute(
                select(_commitments.c.id)
                .where(_commitments.c.operation_id == operation_id)
                .order_by(_commitments.c.id)
                .with_for_update()
            )
        except DBAPIError:
            raise PersistenceUnavailable("lock_failed", "commitment", operation_id) from None


class SqlAlchemyIdempotencyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, operation_name: str, key: str) -> MutationIdempotency | None:
        try:
            row = (
                await self._session.execute(
                    select(_mutation_idempotency).where(
                        _mutation_idempotency.c.operation_name == operation_name,
                        _mutation_idempotency.c.idempotency_key == key,
                    )
                )
            ).first()
            return None if row is None else _idempotency_from_row(_mapping(row))
        except DBAPIError:
            raise PersistenceUnavailable("read_failed", "idempotency") from None

    async def add(self, record: MutationIdempotency) -> None:
        try:
            await self._session.execute(
                insert(_mutation_idempotency).values(_idempotency_to_values(record))
            )
        except IntegrityError:
            raise PersistenceConflict(
                "integrity_constraint", "idempotency", record.operation_id
            ) from None
        except DBAPIError:
            raise PersistenceUnavailable(
                "write_failed", "idempotency", record.operation_id
            ) from None


class SqlAlchemyEvidenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, evidence_id: UUID) -> AgreementEvidence | None:
        return await self._get_by(_agreement_evidence.c.id == evidence_id)

    async def get_by_commitment(self, commitment_id: UUID) -> AgreementEvidence | None:
        return await self._get_by(_agreement_evidence.c.commitment_id == commitment_id)

    async def _get_by(self, criterion: Any) -> AgreementEvidence | None:
        try:
            row = (
                await self._session.execute(select(_agreement_evidence).where(criterion))
            ).first()
            return None if row is None else _evidence_from_row(_mapping(row))
        except DBAPIError:
            raise PersistenceUnavailable("read_failed", "agreement_evidence") from None
        except (InvalidDomainValue, KeyError, TypeError, ValueError):
            raise PersistenceUnavailable("invalid_stored_state", "agreement_evidence") from None

    async def add(self, evidence: AgreementEvidence) -> None:
        try:
            await self._session.execute(
                insert(_agreement_evidence).values(_evidence_to_values(evidence))
            )
        except IntegrityError:
            raise PersistenceConflict(
                "integrity_constraint", "agreement_evidence", evidence.id
            ) from None
        except DBAPIError:
            raise PersistenceUnavailable(
                "write_failed", "agreement_evidence", evidence.id
            ) from None


class SqlAlchemyEvidenceReservationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self, evidence_id: UUID, *, for_update: bool = False
    ) -> EvidenceReservation | None:
        statement = select(_evidence_reservations).where(
            _evidence_reservations.c.id == evidence_id
        )
        if for_update:
            statement = statement.with_for_update()
        try:
            row = (await self._session.execute(statement)).first()
        except DBAPIError:
            raise PersistenceUnavailable(
                "read_failed", "evidence_reservation", evidence_id
            ) from None
        return None if row is None else self._from_row(_mapping(row))

    async def get_by_quote(self, quote_id: UUID) -> EvidenceReservation | None:
        try:
            row = (
                await self._session.execute(
                    select(_evidence_reservations).where(
                        _evidence_reservations.c.quote_id == quote_id
                    )
                )
            ).first()
        except DBAPIError:
            raise PersistenceUnavailable(
                "read_failed", "evidence_reservation", quote_id
            ) from None
        return None if row is None else self._from_row(_mapping(row))

    async def add(self, value: EvidenceReservation) -> None:
        try:
            await self._session.execute(
                insert(_evidence_reservations).values(
                    id=value.id,
                    operation_id=value.operation_id,
                    call_id=value.call_id,
                    quote_id=value.quote_id,
                    recording_reference=value.recording_reference,
                    audio_start_ms=value.audio_start_ms,
                    item_id=value.item_id,
                    event_id=value.event_id,
                    created_at=value.created_at,
                    consumed_by_commitment_id=value.consumed_by_commitment_id,
                )
            )
        except IntegrityError:
            raise PersistenceConflict(
                "integrity_constraint", "evidence_reservation", value.id
            ) from None
        except DBAPIError:
            raise PersistenceUnavailable(
                "write_failed", "evidence_reservation", value.id
            ) from None

    async def consume(
        self, evidence_id: UUID, commitment_id: UUID, call_id: UUID, quote_id: UUID
    ) -> None:
        try:
            changed = (
                await self._session.execute(
                    update(_evidence_reservations)
                    .where(
                        _evidence_reservations.c.id == evidence_id,
                        _evidence_reservations.c.call_id == call_id,
                        _evidence_reservations.c.quote_id == quote_id,
                        _evidence_reservations.c.consumed_by_commitment_id.is_(None),
                    )
                    .values(consumed_by_commitment_id=commitment_id)
                    .returning(_evidence_reservations.c.id)
                )
            ).scalar_one_or_none()
        except DBAPIError:
            raise PersistenceUnavailable(
                "write_failed", "evidence_reservation", evidence_id
            ) from None
        if changed is None:
            from yuno_backend.volta.text_slice.errors import EvidenceReservationMismatch

            raise EvidenceReservationMismatch(quote_id, evidence_id)

    @staticmethod
    def _from_row(row: Mapping[str, Any]) -> EvidenceReservation:
        return EvidenceReservation(
            row["id"],
            row["operation_id"],
            row["call_id"],
            row["quote_id"],
            row["recording_reference"],
            row["audio_start_ms"],
            row["item_id"],
            row["event_id"],
            row["created_at"],
            row["consumed_by_commitment_id"],
        )


class SqlAlchemyBriefRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, brief_id: UUID) -> CallBrief | None:
        return await self._get_by(_call_briefs.c.id == brief_id)

    async def get_by_commitment(self, commitment_id: UUID) -> CallBrief | None:
        return await self._get_by(_call_briefs.c.commitment_id == commitment_id)

    async def list_by_operation(
        self, operation_id: UUID, *, after: tuple[datetime, UUID] | None = None,
        inclusive: bool = False, limit: int | None = None
    ) -> tuple[CallBrief, ...]:
        try:
            rows = (
                await self._session.execute(
                    _ordered_page(
                        select(_call_briefs).where(
                            _call_briefs.c.operation_id == operation_id
                        ),
                        _call_briefs.c.generated_at,
                        _call_briefs.c.id,
                        after=after,
                        inclusive=inclusive,
                        limit=limit,
                    )
                )
            ).all()
            return tuple(_brief_from_row(_mapping(row)) for row in rows)
        except DBAPIError:
            raise PersistenceUnavailable("read_failed", "call_brief", operation_id) from None

    async def _get_by(self, criterion: Any) -> CallBrief | None:
        try:
            row = (await self._session.execute(select(_call_briefs).where(criterion))).first()
            return None if row is None else _brief_from_row(_mapping(row))
        except DBAPIError:
            raise PersistenceUnavailable("read_failed", "call_brief") from None
        except (InvalidDomainValue, KeyError, TypeError, ValueError):
            raise PersistenceUnavailable("invalid_stored_state", "call_brief") from None

    async def add(self, brief: CallBrief) -> None:
        try:
            await self._session.execute(insert(_call_briefs).values(_brief_to_values(brief)))
        except IntegrityError:
            raise PersistenceConflict("integrity_constraint", "call_brief", brief.id) from None
        except DBAPIError:
            raise PersistenceUnavailable("write_failed", "call_brief", brief.id) from None


class SqlAlchemyRecapRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, recap_id: UUID) -> Recap | None:
        return await self._get_by(_recaps.c.id == recap_id)

    async def get_by_commitment(self, commitment_id: UUID) -> Recap | None:
        return await self._get_by(_recaps.c.commitment_id == commitment_id)

    async def list_by_operation(
        self, operation_id: UUID, *, after: tuple[datetime, UUID] | None = None,
        inclusive: bool = False, limit: int | None = None
    ) -> tuple[Recap, ...]:
        try:
            rows = (
                await self._session.execute(
                    _ordered_page(
                        select(_recaps).where(_recaps.c.operation_id == operation_id),
                        _recaps.c.generated_at,
                        _recaps.c.id,
                        after=after,
                        inclusive=inclusive,
                        limit=limit,
                    )
                )
            ).all()
            return tuple(_recap_from_row(_mapping(row)) for row in rows)
        except DBAPIError:
            raise PersistenceUnavailable("read_failed", "recap", operation_id) from None

    async def _get_by(self, criterion: Any) -> Recap | None:
        try:
            row = (await self._session.execute(select(_recaps).where(criterion))).first()
            return None if row is None else _recap_from_row(_mapping(row))
        except DBAPIError:
            raise PersistenceUnavailable("read_failed", "recap") from None
        except (InvalidDomainValue, KeyError, TypeError, ValueError):
            raise PersistenceUnavailable("invalid_stored_state", "recap") from None

    async def add(self, recap: Recap) -> None:
        try:
            await self._session.execute(insert(_recaps).values(_recap_to_values(recap)))
        except IntegrityError:
            raise PersistenceConflict("integrity_constraint", "recap", recap.id) from None
        except DBAPIError:
            raise PersistenceUnavailable("write_failed", "recap", recap.id) from None


class SqlAlchemyPostContactEscalationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, escalation_id: UUID) -> PostContactEscalation | None:
        return await self._get_by(_post_contact_escalations.c.id == escalation_id)

    async def get_unresolved_by_operation(self, operation_id: UUID) -> PostContactEscalation | None:
        return await self._get_by(
            (_post_contact_escalations.c.operation_id == operation_id)
            & (_post_contact_escalations.c.resolved.is_(False))
        )

    async def list_by_operation(
        self, operation_id: UUID, *, after: tuple[datetime, UUID] | None = None,
        inclusive: bool = False, limit: int | None = None
    ) -> tuple[PostContactEscalation, ...]:
        try:
            rows = (
                await self._session.execute(
                    _ordered_page(
                        select(_post_contact_escalations).where(
                            _post_contact_escalations.c.operation_id == operation_id
                        ),
                        _post_contact_escalations.c.created_at,
                        _post_contact_escalations.c.id,
                        after=after,
                        inclusive=inclusive,
                        limit=limit,
                    )
                )
            ).all()
            return tuple(_post_contact_escalation_from_row(_mapping(row)) for row in rows)
        except DBAPIError:
            raise PersistenceUnavailable(
                "read_failed", "post_contact_escalation", operation_id
            ) from None

    async def _get_by(self, criterion: Any) -> PostContactEscalation | None:
        try:
            row = (
                await self._session.execute(select(_post_contact_escalations).where(criterion))
            ).first()
            return None if row is None else _post_contact_escalation_from_row(_mapping(row))
        except DBAPIError:
            raise PersistenceUnavailable("read_failed", "post_contact_escalation") from None
        except (InvalidDomainValue, KeyError, TypeError, ValueError):
            raise PersistenceUnavailable(
                "invalid_stored_state", "post_contact_escalation"
            ) from None

    async def add(self, escalation: PostContactEscalation) -> None:
        try:
            await self._session.execute(
                insert(_post_contact_escalations).values(
                    _post_contact_escalation_to_values(escalation)
                )
            )
        except IntegrityError:
            raise PersistenceConflict(
                "integrity_constraint", "post_contact_escalation", escalation.id
            ) from None
        except DBAPIError:
            raise PersistenceUnavailable(
                "write_failed", "post_contact_escalation", escalation.id
            ) from None

    async def update(self, escalation: PostContactEscalation) -> None:
        try:
            changed = (
                await self._session.execute(
                    update(_post_contact_escalations)
                    .where(_post_contact_escalations.c.id == escalation.id)
                    .values(_post_contact_escalation_to_values(escalation))
                    .returning(_post_contact_escalations.c.id)
                )
            ).scalar_one_or_none()
            if changed is None:
                raise PersistenceConflict("missing_state", "post_contact_escalation", escalation.id)
        except IntegrityError:
            raise PersistenceConflict(
                "integrity_constraint", "post_contact_escalation", escalation.id
            ) from None
        except DBAPIError:
            raise PersistenceUnavailable(
                "write_failed", "post_contact_escalation", escalation.id
            ) from None


class SqlAlchemyRecoveryAttemptRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, attempt_id: UUID) -> RecoveryAttempt | None:
        try:
            row = (
                await self._session.execute(
                    select(_recovery_attempts).where(_recovery_attempts.c.id == attempt_id)
                )
            ).first()
            return None if row is None else _recovery_attempt_from_row(_mapping(row))
        except DBAPIError:
            raise PersistenceUnavailable("read_failed", "recovery_attempt") from None
        except (InvalidDomainValue, KeyError, TypeError, ValueError):
            raise PersistenceUnavailable("invalid_stored_state", "recovery_attempt") from None

    async def list_by_operation(
        self, operation_id: UUID, *, after: tuple[datetime, UUID] | None = None,
        inclusive: bool = False, limit: int | None = None
    ) -> tuple[RecoveryAttempt, ...]:
        try:
            rows = (
                await self._session.execute(
                    _ordered_page(
                        select(_recovery_attempts).where(
                            _recovery_attempts.c.operation_id == operation_id
                        ),
                        _recovery_attempts.c.created_at,
                        _recovery_attempts.c.id,
                        after=after,
                        inclusive=inclusive,
                        limit=limit,
                    )
                )
            ).all()
            return tuple(_recovery_attempt_from_row(_mapping(row)) for row in rows)
        except DBAPIError:
            raise PersistenceUnavailable("read_failed", "recovery_attempt", operation_id) from None

    async def add(self, attempt: RecoveryAttempt) -> None:
        try:
            await self._session.execute(
                insert(_recovery_attempts).values(_recovery_attempt_to_values(attempt))
            )
        except IntegrityError:
            raise PersistenceConflict(
                "integrity_constraint", "recovery_attempt", attempt.id
            ) from None
        except DBAPIError:
            raise PersistenceUnavailable("write_failed", "recovery_attempt", attempt.id) from None


class SqlAlchemyNotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self, notification_id: UUID, *, for_update: bool = False
    ) -> Notification | None:
        try:
            statement = select(_notifications).where(_notifications.c.id == notification_id)
            if for_update:
                statement = statement.with_for_update()
            row = (
                await self._session.execute(statement)
            ).first()
            return None if row is None else _notification_from_row(_mapping(row))
        except DBAPIError:
            raise PersistenceUnavailable("read_failed", "notification") from None
        except (InvalidDomainValue, KeyError, TypeError, ValueError):
            raise PersistenceUnavailable("invalid_stored_state", "notification") from None

    async def list_by_operation(
        self, operation_id: UUID, *, after: tuple[datetime, UUID] | None = None,
        inclusive: bool = False, limit: int | None = None
    ) -> tuple[Notification, ...]:
        try:
            rows = (
                await self._session.execute(
                    _ordered_page(
                        select(_notifications).where(
                            _notifications.c.operation_id == operation_id
                        ),
                        _notifications.c.created_at,
                        _notifications.c.id,
                        after=after,
                        inclusive=inclusive,
                        limit=limit,
                    )
                )
            ).all()
            return tuple(_notification_from_row(_mapping(row)) for row in rows)
        except DBAPIError:
            raise PersistenceUnavailable("read_failed", "notification", operation_id) from None

    async def add(self, notification: Notification) -> None:
        try:
            await self._session.execute(
                insert(_notifications).values(_notification_to_values(notification))
            )
        except IntegrityError:
            raise PersistenceConflict(
                "integrity_constraint", "notification", notification.id
            ) from None
        except DBAPIError:
            raise PersistenceUnavailable("write_failed", "notification", notification.id) from None

    async def update(self, notification: Notification) -> None:
        try:
            changed = (
                await self._session.execute(
                    update(_notifications)
                    .where(_notifications.c.id == notification.id)
                    .values(_notification_to_values(notification))
                    .returning(_notifications.c.id)
                )
            ).scalar_one_or_none()
            if changed is None:
                raise PersistenceConflict("missing_state", "notification", notification.id)
        except IntegrityError:
            raise PersistenceConflict(
                "integrity_constraint", "notification", notification.id
            ) from None
        except DBAPIError:
            raise PersistenceUnavailable("write_failed", "notification", notification.id) from None


class SqlAlchemyTextMutationIdempotencyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lock(self, operation_name: str, key: str) -> None:
        try:
            await self._session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:scope, 0))"),
                {"scope": f"{operation_name}:{key}"},
            )
        except DBAPIError:
            raise PersistenceUnavailable("lock_failed", "text_idempotency") from None

    async def get(self, operation_name: str, key: str) -> TextMutationIdempotency | None:
        try:
            row = (
                await self._session.execute(
                    select(_text_mutation_idempotency).where(
                        _text_mutation_idempotency.c.operation_name == operation_name,
                        _text_mutation_idempotency.c.idempotency_key == key,
                    )
                )
            ).first()
            return None if row is None else _text_idempotency_from_row(_mapping(row))
        except DBAPIError:
            raise PersistenceUnavailable("read_failed", "text_idempotency") from None

    async def add(self, record: TextMutationIdempotency) -> None:
        try:
            await self._session.execute(
                insert(_text_mutation_idempotency).values(_text_idempotency_to_values(record))
            )
        except IntegrityError:
            raise PersistenceConflict(
                "integrity_constraint", "text_idempotency", record.result_id
            ) from None
        except DBAPIError:
            raise PersistenceUnavailable(
                "write_failed", "text_idempotency", record.result_id
            ) from None
