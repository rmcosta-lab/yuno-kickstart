"""Typed application facade for the PostgreSQL-backed text negotiation slice."""

from typing import Protocol
from uuid import UUID

from yuno_backend.volta.evidence.models import AgreementEvidence
from yuno_backend.volta.evidence.repositories import EvidenceStorage, OperationUnitOfWork
from yuno_backend.volta.idempotency import fingerprint, validate_idempotency_key
from yuno_backend.volta.intake.extraction import ExtractionRequest, IntakeExtractor
from yuno_backend.volta.mandates.commands import (
    ApproveOperationCommand,
    CreateIntakeDraftCommand,
)
from yuno_backend.volta.mandates.repositories import Clock, IdGenerator
from yuno_backend.volta.mandates.services import (
    ApproveOperationService,
    CreateIntakeDraftService,
    MandatePolicy,
)
from yuno_backend.volta.negotiations.commands import (
    CreateCommitmentCommand,
    RecordQuoteCommand,
    StartNegotiationCommand,
)
from yuno_backend.volta.negotiations.errors import (
    IdempotencyConflict,
    InvalidNegotiationTransition,
    OperationNotFound,
)
from yuno_backend.volta.negotiations.models import (
    CallState,
    Commitment,
    CommitmentDisposition,
    Negotiation,
    Quote,
)
from yuno_backend.volta.negotiations.repositories import CarrierCatalog
from yuno_backend.volta.negotiations.services import (
    CreateCommitmentService,
    QuoteComparisonService,
    RecordQuoteService,
    StartNegotiationService,
)
from yuno_backend.volta.text_slice.errors import (
    CommitmentEvidenceNotFound,
    EvidenceArtifactUnavailable,
    EvidenceReservationMismatch,
    EvidenceReservationNotFound,
)
from yuno_backend.volta.text_slice.models import (
    ApproveOperationInput,
    AttachCommitmentEvidenceInput,
    AuditProjection,
    AuditQuoteProjection,
    CommitmentProjection,
    CreateCommitmentInput,
    CreateOperationDraftInput,
    DraftProjection,
    EscalationResolutionState,
    EvidenceReservation,
    MutationOutcome,
    NegotiationProjection,
    NegotiationSummaryProjection,
    OperationProjection,
    PreContactEscalationProjection,
    RecordQuoteInput,
    SessionProjection,
    StartNegotiationInput,
)

__all__ = ["OperationUnitOfWorkFactory", "TextNegotiationApplication"]


class OperationUnitOfWorkFactory(Protocol):
    def __call__(self) -> OperationUnitOfWork: ...


class TextNegotiationApplication:
    """Coordinate existing deterministic services behind one transport-free boundary."""

    def __init__(
        self,
        *,
        unit_of_work_factory: OperationUnitOfWorkFactory,
        extractor: IntakeExtractor,
        carrier_catalog: CarrierCatalog,
        clock: Clock,
        id_generator: IdGenerator,
        evidence_storage: EvidenceStorage,
        extraction_policy_version: str,
    ) -> None:
        self._uow_factory = unit_of_work_factory
        self._extractor = extractor
        self._catalog = carrier_catalog
        self._clock = clock
        self._ids = id_generator
        self._evidence_storage = evidence_storage
        self._policy_version = extraction_policy_version

    async def create_operation_draft(
        self, command: CreateOperationDraftInput
    ) -> MutationOutcome[DraftProjection]:
        proposal = await self._extractor.extract(
            ExtractionRequest(
                source_prompt=command.source_prompt,
                requested_language=command.requested_language,
                extraction_policy_version=self._policy_version,
            )
        )
        draft, replayed = await CreateIntakeDraftService(
            self._uow_factory(), self._clock, self._ids
        ).create_with_replay(
            CreateIntakeDraftCommand(
                source_prompt=command.source_prompt,
                requested_language=command.requested_language,
                extraction_policy_version=self._policy_version,
                proposal=proposal,
            ),
            command.idempotency_key,
        )
        return MutationOutcome(DraftProjection(draft), replayed)

    async def approve_operation(
        self, command: ApproveOperationInput
    ) -> MutationOutcome[OperationProjection]:
        operation, replayed = await ApproveOperationService(
            self._uow_factory(), self._clock, self._ids
        ).approve_with_replay(
            ApproveOperationCommand(
                draft_id=command.draft_id,
                expected_draft_version=command.expected_draft_version,
                approval_actor=command.approval_actor,
                correlation_id=command.correlation_id,
            ),
            command.idempotency_key,
        )
        return MutationOutcome(await self.get_operation(operation.id), replayed)

    async def get_operation(self, operation_id: UUID) -> OperationProjection:
        uow = self._uow_factory()
        async with uow:
            operation = await uow.operations.get(operation_id)
            if operation is None:
                raise OperationNotFound(operation_id)
            negotiation = await uow.negotiations.get_by_operation(operation_id)
            quotes = await uow.quotes.list_by_operation(operation_id)
            commitments = await uow.commitments.list_by_operation(operation_id)
            commitment_history = await self._project_commitments(uow, commitments)
            events = await uow.audit_events.list_by_operation(operation_id)
        comparison = self._comparison(operation_id, operation.mandate.version, quotes)
        updated_at = operation.status_history[-1].occurred_at
        negotiation_projection = (
            None if negotiation is None else self._project_negotiation(negotiation)
        )
        summary = (
            None
            if negotiation is None
            else NegotiationSummaryProjection(
                negotiation.id,
                len(negotiation.sessions),
                sum(session.state is CallState.ACTIVE for session in negotiation.sessions),
                0 if comparison is None else len(comparison.ranked_quotes),
            )
        )
        return OperationProjection(
            operation,
            negotiation_projection,
            summary,
            quotes,
            comparison,
            next(
                (
                    item
                    for item in commitment_history
                    if item.commitment.disposition is CommitmentDisposition.ACTIVE
                ),
                None,
            ),
            events,
            updated_at,
        )

    async def start_negotiation(
        self, command: StartNegotiationInput
    ) -> MutationOutcome[NegotiationProjection]:
        uow = self._uow_factory()
        async with uow:
            operation = await uow.operations.get(command.operation_id)
            if operation is None:
                raise OperationNotFound(command.operation_id)
        negotiation, replayed = await StartNegotiationService(
            self._uow_factory(), self._catalog, self._clock, self._ids
        ).start_with_replay(
            StartNegotiationCommand(
                operation_id=command.operation_id,
                expected_operation_version=command.expected_operation_version,
                mandate_version=operation.mandate.version,
                channel=command.channel,
                idempotency_key=command.idempotency_key,
                correlation_id=command.correlation_id,
            )
        )
        return MutationOutcome(self._project_negotiation(negotiation), replayed)

    async def record_quote(self, command: RecordQuoteInput) -> MutationOutcome[Quote]:
        quote, replayed = await RecordQuoteService(
            self._uow_factory(), MandatePolicy(), self._clock, self._ids
        ).record_with_replay(
            RecordQuoteCommand(
                call_id=command.call_id,
                expected_operation_version=command.expected_operation_version,
                carrier_id=command.carrier_id,
                mandate_version=command.mandate_version,
                terms=command.terms,
                valid_until=command.valid_until,
                idempotency_key=command.idempotency_key,
                correlation_id=command.correlation_id,
            )
        )
        return MutationOutcome(quote, replayed)

    async def create_candidate_commitment(
        self, command: CreateCommitmentInput
    ) -> MutationOutcome[CommitmentProjection]:
        service_command = CreateCommitmentCommand(
            call_id=command.call_id,
            expected_operation_version=command.expected_operation_version,
            quote_id=command.quote_id,
            mandate_version=command.mandate_version,
            evidence_id=command.evidence_id,
            idempotency_key=command.idempotency_key,
            correlation_id=command.correlation_id,
        )
        replay = await self._commitment_replay(service_command)
        if replay is not None:
            return MutationOutcome(replay, True)

        reservation = await self._evidence_reservation(
            command.evidence_id, command.call_id, command.quote_id
        )
        commitment_id = self._ids.new_id()
        evidence = AgreementEvidence(
            id=reservation.id,
            commitment_id=commitment_id,
            recording_reference=reservation.recording_reference,
            audio_start_ms=reservation.audio_start_ms,
            item_id=reservation.item_id,
            event_id=reservation.event_id,
            created_at=reservation.created_at,
        )
        (commitment, persisted_evidence), replayed = await CreateCommitmentService(
            self._uow_factory(), MandatePolicy(), self._clock, self._ids
        ).create_with_evidence_with_replay(service_command, evidence)
        return MutationOutcome(CommitmentProjection(commitment, persisted_evidence), replayed)

    async def attach_commitment_evidence(
        self, command: AttachCommitmentEvidenceInput
    ) -> MutationOutcome[EvidenceReservation]:
        validate_idempotency_key(command.idempotency_key)
        replay = await self._evidence_reservation_replay(command)
        if replay is not None:
            return MutationOutcome(replay, True)
        try:
            payload = await self._evidence_storage.retrieve(command.recording_reference)
        except (FileNotFoundError, OSError, ValueError):
            raise EvidenceArtifactUnavailable(command.recording_reference) from None
        if not payload:
            raise EvidenceArtifactUnavailable(command.recording_reference)

        expected_fingerprint = fingerprint(
            command, exclude=("idempotency_key", "correlation_id")
        )
        uow = self._uow_factory()
        async with uow:
            try:
                replay_record = await uow.idempotency.get(
                    "attach_commitment_evidence", command.idempotency_key
                )
                if replay_record is not None:
                    if replay_record.fingerprint != expected_fingerprint:
                        raise IdempotencyConflict(
                            replay_record.operation_id,
                            "attach_commitment_evidence",
                            command.idempotency_key,
                        )
                    replay = await uow.evidence_reservations.get(replay_record.result_id)
                    if replay is None:
                        raise InvalidNegotiationTransition(
                            replay_record.operation_id, "idempotency_result_missing"
                        )
                    await uow.rollback()
                    return MutationOutcome(replay, True)
                negotiation = await uow.negotiations.get_by_call(command.call_id)
                if negotiation is None:
                    raise InvalidNegotiationTransition(command.call_id, "call_session_not_found")
                operation = await uow.operations.get(negotiation.operation_id, for_update=True)
                if operation is None:
                    raise OperationNotFound(negotiation.operation_id)
                if operation.version != command.expected_operation_version:
                    from yuno_backend.volta.negotiations.errors import StaleOperationVersion

                    raise StaleOperationVersion(
                        operation.id, command.expected_operation_version, operation.version
                    )
                quotes = await uow.quotes.list_by_operation(operation.id)
                comparison = self._comparison(operation.id, operation.mandate.version, quotes)
                selected_id = None if comparison is None else comparison.selected_quote_id
                quote = next(
                    (
                        item
                        for item in quotes
                        if item.id == selected_id and item.call_id == command.call_id
                    ),
                    None,
                )
                if quote is None:
                    raise InvalidNegotiationTransition(operation.id, "agreement_quote_missing")
                existing = await uow.evidence_reservations.get_by_quote(quote.id)
                if existing is not None:
                    raise EvidenceReservationMismatch(quote.id, existing.id)
                now = self._clock.now()
                reservation = EvidenceReservation(
                    self._ids.new_id(),
                    operation.id,
                    command.call_id,
                    quote.id,
                    command.recording_reference,
                    command.audio_start_ms,
                    command.item_id,
                    command.event_id,
                    now,
                )
                await uow.evidence_reservations.add(reservation)
                from yuno_backend.volta.negotiations.models import MutationIdempotency

                await uow.idempotency.add(
                    MutationIdempotency(
                        operation.id,
                        "attach_commitment_evidence",
                        command.idempotency_key,
                        expected_fingerprint,
                        reservation.id,
                        now,
                    )
                )
                await uow.commit()
                return MutationOutcome(reservation, False)
            except Exception:
                await uow.rollback()
                raise

    async def _evidence_reservation_replay(
        self, command: AttachCommitmentEvidenceInput
    ) -> EvidenceReservation | None:
        expected_fingerprint = fingerprint(
            command, exclude=("idempotency_key", "correlation_id")
        )
        uow = self._uow_factory()
        async with uow:
            record = await uow.idempotency.get(
                "attach_commitment_evidence", command.idempotency_key
            )
            if record is None:
                return None
            if record.fingerprint != expected_fingerprint:
                raise IdempotencyConflict(
                    record.operation_id,
                    "attach_commitment_evidence",
                    command.idempotency_key,
                )
            reservation = await uow.evidence_reservations.get(record.result_id)
            if reservation is None:
                raise InvalidNegotiationTransition(
                    record.operation_id, "idempotency_result_missing"
                )
            return reservation

    async def _evidence_reservation(
        self, evidence_id: UUID, call_id: UUID, quote_id: UUID
    ) -> EvidenceReservation:
        uow = self._uow_factory()
        async with uow:
            reservation = await uow.evidence_reservations.get(evidence_id)
            if reservation is None or reservation.consumed_by_commitment_id is not None:
                raise EvidenceReservationNotFound(evidence_id)
            if reservation.call_id != call_id or reservation.quote_id != quote_id:
                raise EvidenceReservationMismatch(quote_id, evidence_id)
            return reservation

    async def get_operation_audit(self, operation_id: UUID) -> AuditProjection:
        projection = await self.get_operation(operation_id)
        sessions = () if projection.negotiation is None else projection.negotiation.sessions
        labels = {
            projected.session.call_id: projected.session.carrier_display_label
            for projected in sessions
        }
        selected_id = (
            None
            if projection.quote_comparison is None
            else projection.quote_comparison.selected_quote_id
        )
        ranked = (
            ()
            if projection.quote_comparison is None
            else projection.quote_comparison.ranked_quotes
        )
        ranked_ids = {quote.id for quote in ranked}
        comparison_quotes = (
            *ranked,
            *(quote for quote in projection.quotes if quote.id not in ranked_ids),
        )
        try:
            rows = tuple(
                AuditQuoteProjection(
                    quote,
                    labels[quote.call_id],
                    quote.id == selected_id,
                )
                for quote in comparison_quotes
            )
        except KeyError:
            raise InvalidNegotiationTransition(
                operation_id, "quote_session_projection_missing"
            ) from None
        return AuditProjection(
            operation_id,
            projection.audit_events,
            projection.negotiation,
            rows,
            await self._commitment_history(operation_id),
        )

    async def _commitment_replay(
        self, command: CreateCommitmentCommand
    ) -> CommitmentProjection | None:
        expected_fingerprint = fingerprint(
            command, exclude=("idempotency_key", "correlation_id")
        )
        uow = self._uow_factory()
        async with uow:
            record = await uow.idempotency.get(
                "create_commitment", command.idempotency_key
            )
            if record is None:
                return None
            if record.fingerprint != expected_fingerprint:
                raise IdempotencyConflict(
                    record.operation_id, "create_commitment", command.idempotency_key
                )
            commitment = await uow.commitments.get(record.result_id)
            if commitment is None:
                raise InvalidNegotiationTransition(
                    record.operation_id, "idempotency_result_missing"
                )
            evidence = await uow.evidence.get_by_commitment(commitment.id)
            if evidence is None:
                raise CommitmentEvidenceNotFound(commitment.id, commitment.evidence_id)
            return CommitmentProjection(commitment, evidence)

    async def _commitment_history(
        self, operation_id: UUID
    ) -> tuple[CommitmentProjection, ...]:
        uow = self._uow_factory()
        async with uow:
            commitments = await uow.commitments.list_by_operation(operation_id)
            return await self._project_commitments(uow, commitments)

    @staticmethod
    async def _project_commitments(
        uow: OperationUnitOfWork,
        commitments: tuple[Commitment, ...],
    ) -> tuple[CommitmentProjection, ...]:
        projected: list[CommitmentProjection] = []
        for commitment in _ordered_commitment_history(commitments):
            evidence = await uow.evidence.get_by_commitment(commitment.id)
            projected.append(CommitmentProjection(commitment, evidence))
        return tuple(projected)

    @staticmethod
    def _project_negotiation(negotiation: Negotiation) -> NegotiationProjection:
        sessions = tuple(
            SessionProjection(
                session,
                (
                    "Covers the requested route",
                    "Declared available at selection",
                    f"Fixed priority {session.fixed_priority}; "
                    f"selected rank {session.selection_rank}",
                ),
            )
            for session in negotiation.sessions
        )
        escalation = negotiation.pre_contact_escalation
        escalation_projection = (
            None
            if escalation is None
            else PreContactEscalationProjection(
                escalation,
                "No eligible synthetic carrier passed route and availability checks.",
                ("Route coverage checked", "Declared availability checked"),
                "Review the route or synthetic availability before retrying.",
                EscalationResolutionState.OPEN,
            )
        )
        return NegotiationProjection(negotiation, sessions, escalation_projection)

    def _comparison(
        self,
        operation_id: UUID,
        mandate_version: int,
        quotes: tuple[Quote, ...],
    ):
        if not quotes:
            return None
        return QuoteComparisonService(self._clock).compare(
            operation_id, mandate_version, quotes
        )


def _ordered_commitment_history(
    commitments: tuple[Commitment, ...],
) -> tuple[Commitment, ...]:
    """Order winner history by its explicit replacement lineage."""
    by_id = {commitment.id: commitment for commitment in commitments}
    roots = sorted(
        (
            commitment
            for commitment in commitments
            if commitment.replaces_commitment_id not in by_id
        ),
        key=lambda commitment: (commitment.created_at, commitment.id),
    )
    ordered: list[Commitment] = []
    for root in roots:
        current: Commitment | None = root
        while current is not None and current not in ordered:
            ordered.append(current)
            current = (
                None
                if current.replaced_by_commitment_id is None
                else by_id.get(current.replaced_by_commitment_id)
            )
    ordered.extend(commitment for commitment in commitments if commitment not in ordered)
    return tuple(ordered)
