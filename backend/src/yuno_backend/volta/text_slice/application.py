"""Typed application facade for the PostgreSQL-backed text negotiation slice."""

import base64
import json
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Protocol
from uuid import UUID

from yuno_backend.volta.audit.models import AuditEvent
from yuno_backend.volta.evidence.commands import GenerateBriefCommand, GenerateRecapCommand
from yuno_backend.volta.evidence.models import AgreementEvidence, CallBrief, Recap
from yuno_backend.volta.evidence.repositories import EvidenceStorage, OperationUnitOfWork
from yuno_backend.volta.evidence.services import GenerateBriefService, GenerateRecapService
from yuno_backend.volta.idempotency import (
    TextMutationIdempotency,
    fingerprint,
    validate_idempotency_key,
)
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
from yuno_backend.volta.recovery.commands import (
    AcknowledgeNotificationCommand,
    CreateEscalationCommand,
    ReplaceMandateCommand,
    SimulateInboundRecoveryCommand,
)
from yuno_backend.volta.recovery.fixtures import (
    DeterministicRecoveryFixtureCatalog,
    RecoveryFixtureCatalog,
)
from yuno_backend.volta.recovery.models import (
    Notification,
    PostContactEscalation,
    RecoveryAttempt,
)
from yuno_backend.volta.recovery.services import (
    AcknowledgeNotificationService,
    CreateEscalationService,
    ReplaceMandateService,
    SimulateInboundRecoveryService,
)
from yuno_backend.volta.text_slice.errors import (
    CommitmentEvidenceNotFound,
    EvidenceArtifactUnavailable,
    EvidenceReservationMismatch,
    EvidenceReservationNotFound,
)
from yuno_backend.volta.text_slice.models import (
    AcknowledgeNotificationInput,
    ApproveOperationInput,
    AttachCommitmentEvidenceInput,
    AuditProjection,
    AuditQuery,
    AuditQuoteProjection,
    CommitmentProjection,
    CreateCallBriefInput,
    CreateCommitmentInput,
    CreateEscalationInput,
    CreateOperationDraftInput,
    CreateSimulatedRecapInput,
    DraftProjection,
    EscalationResolutionState,
    EvidenceReservation,
    MutationOutcome,
    NegotiationProjection,
    NegotiationSummaryProjection,
    OperationProjection,
    PreContactEscalationProjection,
    RecordQuoteInput,
    RecoveryProjection,
    ReplaceMandateInput,
    SessionProjection,
    StartInboundRecoveryInput,
    StartNegotiationInput,
)
from yuno_backend.volta.text_slice.snapshots import decode_snapshot, encode_snapshot

__all__ = ["OperationUnitOfWorkFactory", "TextNegotiationApplication"]

_MAX_PROJECTION_ROWS = 100


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
        recovery_fixture_catalog: RecoveryFixtureCatalog | None = None,
        extraction_policy_version: str,
    ) -> None:
        self._uow_factory = unit_of_work_factory
        self._extractor = extractor
        self._catalog = carrier_catalog
        self._clock = clock
        self._ids = id_generator
        self._evidence_storage = evidence_storage
        self._recovery_fixtures = (
            DeterministicRecoveryFixtureCatalog()
            if recovery_fixture_catalog is None
            else recovery_fixture_catalog
        )
        self._policy_version = extraction_policy_version

    async def create_operation_draft(
        self, command: CreateOperationDraftInput
    ) -> MutationOutcome[DraftProjection]:
        proposal = await self._extractor.extract(
            ExtractionRequest(
                source_prompt=command.source_prompt,
                requested_language=command.requested_language,
                extraction_policy_version=self._policy_version,
                reference_date=self._clock.now().date(),
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
            return await self._get_operation_from_uow(uow, operation_id)

    async def _get_operation_from_uow(
        self,
        uow: OperationUnitOfWork,
        operation_id: UUID,
        *,
        include_audit_events: bool = True,
        enforce_projection_bounds: bool = True,
    ) -> OperationProjection:
        operation = await uow.operations.get(operation_id)
        if operation is None:
            raise OperationNotFound(operation_id)
        negotiation = await uow.negotiations.get_by_operation(operation_id)
        quotes = self._bounded_projection(
            operation_id,
            "quotes",
            await uow.quotes.list_by_operation(
                operation_id, limit=_MAX_PROJECTION_ROWS + 1
            ),
            enforce=enforce_projection_bounds,
        )
        commitments = self._bounded_projection(
            operation_id,
            "commitments",
            await uow.commitments.list_by_operation(
                operation_id, limit=_MAX_PROJECTION_ROWS + 1
            ),
            enforce=enforce_projection_bounds,
        )
        commitment_history = await self._project_commitments(uow, commitments)
        events = (
            self._bounded_projection(
                operation_id,
                "audit_events",
                await uow.audit_events.list_by_operation(
                    operation_id, limit=_MAX_PROJECTION_ROWS + 1
                ),
                enforce=enforce_projection_bounds,
            )
            if include_audit_events
            else ()
        )
        open_escalation = await uow.post_contact_escalations.get_unresolved_by_operation(
            operation_id
        )
        notifications = self._bounded_projection(
            operation_id,
            "notifications",
            await uow.notifications.list_by_operation(
                operation_id, limit=_MAX_PROJECTION_ROWS + 1
            ),
            enforce=enforce_projection_bounds,
        )
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
            operation=operation,
            negotiation=negotiation_projection,
            negotiation_summary=summary,
            quotes=quotes,
            quote_comparison=comparison,
            active_commitment=next(
                (
                    item
                    for item in commitment_history
                    if item.commitment.disposition is CommitmentDisposition.ACTIVE
                ),
                None,
            ),
            audit_events=events,
            updated_at=updated_at,
            open_escalation=open_escalation,
            notifications=notifications,
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
                quotes = self._bounded_projection(
                    operation.id,
                    "quotes",
                    await uow.quotes.list_by_operation(
                        operation.id, limit=_MAX_PROJECTION_ROWS + 1
                    ),
                )
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

    async def create_simulated_recap(
        self, command: CreateSimulatedRecapInput
    ) -> MutationOutcome[Recap]:
        async def mutate(uow: OperationUnitOfWork) -> Recap:
            negotiation = await uow.negotiations.get_by_call(command.call_id)
            if negotiation is None:
                raise InvalidNegotiationTransition(command.call_id, "call_session_not_found")
            return await GenerateRecapService(uow, self._clock, self._ids).generate_in_transaction(
                GenerateRecapCommand(
                    negotiation.operation_id,
                    command.call_id,
                    command.expected_operation_version,
                    command.commitment_id,
                    command.rendered_content,
                    command.correlation_id,
                )
            )

        return await self._atomic_mutation(
            "create_simulated_recap", command, Recap, mutate
        )

    async def create_call_brief(
        self, command: CreateCallBriefInput
    ) -> MutationOutcome[CallBrief]:
        async def mutate(uow: OperationUnitOfWork) -> CallBrief:
            negotiation = await uow.negotiations.get_by_call(command.call_id)
            if negotiation is None:
                raise InvalidNegotiationTransition(command.call_id, "call_session_not_found")
            active = await uow.commitments.get_active(negotiation.operation_id)
            if active is None or active.call_id != command.call_id:
                raise InvalidNegotiationTransition(
                    negotiation.operation_id, "active_commitment_for_call_missing"
                )
            return await GenerateBriefService(uow, self._clock, self._ids).generate_in_transaction(
                GenerateBriefCommand(
                    negotiation.operation_id,
                    command.call_id,
                    command.expected_operation_version,
                    active.id,
                    command.facts,
                    command.objections,
                    command.changes,
                    command.unresolved_items,
                    command.correlation_id,
                )
            )

        return await self._atomic_mutation("create_call_brief", command, CallBrief, mutate)

    async def start_inbound_recovery(
        self, command: StartInboundRecoveryInput
    ) -> MutationOutcome[RecoveryProjection]:
        replay = await self._read_replay(
            "start_inbound_simulation", command, RecoveryProjection
        )
        if replay is not None:
            return MutationOutcome(replay, True)
        fixture = self._recovery_fixtures.get(command.scenario)
        if fixture.evidence is not None:
            try:
                payload = await self._evidence_storage.retrieve(
                    fixture.evidence.recording_reference
                )
            except (FileNotFoundError, OSError, ValueError):
                raise EvidenceArtifactUnavailable(
                    fixture.evidence.recording_reference
                ) from None
            if not payload:
                raise EvidenceArtifactUnavailable(fixture.evidence.recording_reference)

        async def mutate(uow: OperationUnitOfWork) -> RecoveryProjection:
            attempt = await SimulateInboundRecoveryService(
                uow, MandatePolicy(), self._clock, self._ids
            ).simulate_in_transaction(
                SimulateInboundRecoveryCommand(
                    operation_id=command.operation_id,
                    expected_operation_version=command.expected_operation_version,
                    commitment_id=command.active_commitment_id,
                    mandate_version=(
                        await self._required_operation(uow, command.operation_id)
                    ).mandate.version,
                    proposed_terms=fixture.proposed_terms,
                    correlation_id=command.correlation_id,
                    scenario=fixture.scenario,
                    decision_reason=fixture.decision_reason,
                    evidence=fixture.evidence,
                    escalation_context=fixture.escalation_context,
                )
            )
            return await self._project_recovery(uow, attempt)

        return await self._atomic_mutation(
            "start_inbound_simulation", command, RecoveryProjection, mutate
        )

    async def start_inbound_simulation(
        self, command: StartInboundRecoveryInput
    ) -> MutationOutcome[RecoveryProjection]:
        return await self.start_inbound_recovery(command)

    async def replace_mandate(
        self, command: ReplaceMandateInput
    ) -> MutationOutcome[OperationProjection]:
        async def mutate(uow: OperationUnitOfWork) -> OperationProjection:
            await ReplaceMandateService(
                uow, MandatePolicy(), self._clock, self._ids
            ).replace_in_transaction(
                ReplaceMandateCommand(
                    command.operation_id,
                    command.expected_operation_version,
                    command.resolved_escalation_id,
                    command.maximum_amount,
                    command.pickup_window,
                    command.allowed_conditions,
                    command.escalation_conditions,
                    command.approval_actor,
                    command.correlation_id,
                )
            )
            return await self._get_operation_from_uow(uow, command.operation_id)

        return await self._atomic_mutation(
            "replace_mandate", command, OperationProjection, mutate
        )

    async def create_escalation(
        self, command: CreateEscalationInput
    ) -> MutationOutcome[PostContactEscalation]:
        async def mutate(uow: OperationUnitOfWork) -> PostContactEscalation:
            return await CreateEscalationService(
                uow, self._clock, self._ids
            ).create_in_transaction(
                CreateEscalationCommand(
                    command.call_id,
                    command.expected_operation_version,
                    command.conflict,
                    command.attempted_alternatives,
                    command.recommended_action,
                    command.correlation_id,
                )
            )

        return await self._atomic_mutation(
            "create_escalation", command, PostContactEscalation, mutate
        )

    async def acknowledge_notification(
        self, command: AcknowledgeNotificationInput
    ) -> MutationOutcome[Notification]:
        async def mutate(uow: OperationUnitOfWork) -> Notification:
            return await AcknowledgeNotificationService(
                uow, self._clock, self._ids
            ).acknowledge_in_transaction(
                AcknowledgeNotificationCommand(
                    command.notification_id,
                    command.expected_operation_version,
                    command.acknowledged_by,
                    command.correlation_id,
                )
            )

        return await self._atomic_mutation(
            "acknowledge_notification", command, Notification, mutate
        )

    async def _atomic_mutation[T](
        self,
        operation_name: str,
        command: object,
        result_type: type[T],
        mutate: Callable[[OperationUnitOfWork], Awaitable[T]],
    ) -> MutationOutcome[T]:
        key = command.idempotency_key
        validate_idempotency_key(key)
        expected_fingerprint = fingerprint(
            command, exclude=("idempotency_key", "correlation_id")
        )
        uow = self._uow_factory()
        async with uow:
            try:
                await uow.text_idempotency.lock(operation_name, key)
                record = await uow.text_idempotency.get(operation_name, key)
                if record is not None:
                    if record.fingerprint != expected_fingerprint:
                        raise IdempotencyConflict(record.result_id, operation_name, key)
                    result = decode_snapshot(record.result_snapshot, result_type)
                    await uow.rollback()
                    return MutationOutcome(result, True)
                result = await mutate(uow)
                result_id = self._result_id(result)
                now = self._clock.now()
                await uow.text_idempotency.add(
                    TextMutationIdempotency(
                        operation_name,
                        key,
                        expected_fingerprint,
                        result_id,
                        now,
                        result_type.__name__,
                        encode_snapshot(result),
                    )
                )
                await uow.commit()
                return MutationOutcome(result, False)
            except Exception:
                await uow.rollback()
                raise

    async def _read_replay[T](
        self, operation_name: str, command: object, result_type: type[T]
    ) -> T | None:
        key = command.idempotency_key
        validate_idempotency_key(key)
        expected_fingerprint = fingerprint(
            command, exclude=("idempotency_key", "correlation_id")
        )
        uow = self._uow_factory()
        async with uow:
            record = await uow.text_idempotency.get(operation_name, key)
            if record is None:
                return None
            if record.fingerprint != expected_fingerprint:
                raise IdempotencyConflict(record.result_id, operation_name, key)
            return decode_snapshot(record.result_snapshot, result_type)

    @staticmethod
    async def _required_operation(uow: OperationUnitOfWork, operation_id: UUID):
        operation = await uow.operations.get(operation_id)
        if operation is None:
            raise OperationNotFound(operation_id)
        return operation

    @staticmethod
    def _result_id(result: object) -> UUID:
        for name in ("id", "operation_id", "notification_id"):
            value = getattr(result, name, None)
            if isinstance(value, UUID):
                return value
        if isinstance(result, OperationProjection):
            return result.operation.id
        if isinstance(result, RecoveryProjection):
            return result.attempt.id
        raise InvalidNegotiationTransition(UUID(int=0), "mutation_result_id_missing")

    async def get_operation_audit(
        self, query: UUID | AuditQuery
    ) -> AuditProjection:
        audit_query = AuditQuery(query) if isinstance(query, UUID) else query
        operation_id = audit_query.operation_id
        boundary = self._decode_cursor(audit_query.cursor)
        after = None if boundary is None else boundary[:2]
        per_type_limit = audit_query.limit + 2
        uow = self._uow_factory()
        async with uow:
            await uow.stabilize_read_snapshot()
            # The audit is a paginated timeline, not an operation-detail
            # projection.  In particular, do not pre-load the detail
            # projection here: it deliberately rejects histories over
            # ``_MAX_PROJECTION_ROWS`` while this method must page them.
            operation = await self._required_operation(uow, operation_id)
            negotiation = await uow.negotiations.get_by_operation(operation_id)
            negotiation_projection = (
                None
                if negotiation is None
                else self._project_negotiation(negotiation)
            )
            sessions = (
                ()
                if negotiation_projection is None
                else negotiation_projection.sessions
            )
            labels = {
                projected.session.call_id: projected.session.carrier_display_label
                for projected in sessions
            }
            quotes = await uow.quotes.list_by_operation(
                operation_id,
                after=after,
                inclusive=boundary is not None,
                limit=per_type_limit,
            )
            commitment_history = await self._project_commitments(
                uow,
                await uow.commitments.list_by_operation(
                    operation_id,
                    after=after,
                    inclusive=boundary is not None,
                    limit=per_type_limit,
                ),
            )
            recaps = await uow.recaps.list_by_operation(
                operation_id, after=after, inclusive=boundary is not None,
                limit=per_type_limit
            )
            briefs = await uow.briefs.list_by_operation(
                operation_id, after=after, inclusive=boundary is not None,
                limit=per_type_limit
            )
            attempts = await uow.recovery_attempts.list_by_operation(
                operation_id, after=after, inclusive=boundary is not None,
                limit=per_type_limit
            )
            escalations = await uow.post_contact_escalations.list_by_operation(
                operation_id, after=after, inclusive=boundary is not None,
                limit=per_type_limit
            )
            notifications = await uow.notifications.list_by_operation(
                operation_id, after=after, inclusive=boundary is not None,
                limit=per_type_limit
            )
            events = await uow.audit_events.list_by_operation(
                operation_id, after=after, inclusive=boundary is not None,
                limit=per_type_limit
            )
            recoveries: list[RecoveryProjection] = []
            for attempt in attempts:
                recoveries.append(await self._project_recovery(uow, attempt))

        page_comparison = self._comparison(
            operation_id, operation.mandate.version, quotes
        )
        selected_id = (
            None if page_comparison is None else page_comparison.selected_quote_id
        )
        page_ranked = () if page_comparison is None else page_comparison.ranked_quotes
        page_ranked_ids = {quote.id for quote in page_ranked}
        comparison_page_quotes = (
            *page_ranked,
            *(quote for quote in quotes if quote.id not in page_ranked_ids),
        )
        try:
            audit_quote_rows = tuple(
                AuditQuoteProjection(
                    quote, labels[quote.call_id], quote.id == selected_id
                )
                for quote in comparison_page_quotes
            )
        except KeyError:
            raise InvalidNegotiationTransition(
                operation_id, "quote_session_projection_missing"
            ) from None

        timeline: list[tuple[datetime, UUID, str, object]] = []
        timeline.extend(
            (event.occurred_at, event.event_id, "event", event)
            for event in events
        )
        timeline.extend(
            (row.quote.created_at, row.quote.id, "quote", row)
            for row in audit_quote_rows
        )
        timeline.extend(
            (item.commitment.created_at, item.commitment.id, "commitment", item)
            for item in commitment_history
        )
        timeline.extend((item.generated_at, item.id, "recap", item) for item in recaps)
        timeline.extend((item.generated_at, item.id, "brief", item) for item in briefs)
        timeline.extend(
            (item.attempt.created_at, item.attempt.id, "recovery", item)
            for item in recoveries
        )
        timeline.extend(
            (item.created_at, item.id, "escalation", item) for item in escalations
        )
        timeline.extend(
            (item.created_at, item.id, "notification", item) for item in notifications
        )
        timeline.sort(key=lambda item: (item[0], item[1], item[2]))
        if boundary is not None:
            if not any(item[:3] == boundary for item in timeline):
                raise InvalidNegotiationTransition(
                    operation_id, "audit_cursor_boundary_missing"
                )
            timeline = [item for item in timeline if item[:3] > boundary]
        page = timeline[: audit_query.limit + 1]
        has_more = len(page) > audit_query.limit
        selected = page[: audit_query.limit]
        next_cursor = (
            self._encode_cursor(selected[-1][:3]) if has_more and selected else None
        )

        def selected_kind[T](kind: str, expected: type[T]) -> tuple[T, ...]:
            return tuple(
                item[3] for item in selected if item[2] == kind and isinstance(item[3], expected)
            )

        selected_quote_ids = {item[1] for item in selected if item[2] == "quote"}
        selected_quotes = tuple(
            row for row in audit_quote_rows if row.quote.id in selected_quote_ids
        )

        return AuditProjection(
            operation_id,
            selected_kind("event", AuditEvent),
            negotiation_projection,
            selected_quotes,
            selected_kind("commitment", CommitmentProjection),
            selected_kind("recap", Recap),
            selected_kind("brief", CallBrief),
            selected_kind("recovery", RecoveryProjection),
            selected_kind("escalation", PostContactEscalation),
            selected_kind("notification", Notification),
            next_cursor,
        )

    @staticmethod
    async def _project_recovery(
        uow: OperationUnitOfWork, attempt: RecoveryAttempt
    ) -> RecoveryProjection:
        active = None
        if attempt.resulting_commitment_id is not None:
            commitment = await uow.commitments.get(attempt.resulting_commitment_id)
            if commitment is None:
                raise InvalidNegotiationTransition(
                    attempt.operation_id, "recovery_commitment_projection_missing"
                )
            evidence = await uow.evidence.get_by_commitment(commitment.id)
            if evidence is None:
                raise CommitmentEvidenceNotFound(commitment.id, commitment.evidence_id)
            active = CommitmentProjection(commitment, evidence)
        escalation = (
            None
            if attempt.escalation_id is None
            else await uow.post_contact_escalations.get(attempt.escalation_id)
        )
        if attempt.escalation_id is not None and escalation is None:
            raise InvalidNegotiationTransition(
                attempt.operation_id, "recovery_escalation_projection_missing"
            )
        return RecoveryProjection(attempt, active, escalation)

    @staticmethod
    def _bounded_projection[T](
        operation_id: UUID,
        kind: str,
        values: tuple[T, ...],
        *,
        enforce: bool = True,
    ) -> tuple[T, ...]:
        if enforce and len(values) > _MAX_PROJECTION_ROWS:
            raise InvalidNegotiationTransition(
                operation_id, f"operation_projection_{kind}_overflow"
            )
        return values

    @staticmethod
    def _encode_cursor(boundary: tuple[datetime, UUID, str]) -> str:
        payload = json.dumps(
            [boundary[0].isoformat(), str(boundary[1]), boundary[2]],
            separators=(",", ":"),
        ).encode()
        return base64.urlsafe_b64encode(payload).decode().rstrip("=")

    @staticmethod
    def _decode_cursor(cursor: str | None) -> tuple[datetime, UUID, str] | None:
        if cursor is None:
            return None
        try:
            padding = "=" * (-len(cursor) % 4)
            value = json.loads(base64.urlsafe_b64decode(cursor + padding))
            if (
                not isinstance(value, list)
                or len(value) != 3
                or value[2]
                not in {
                    "event",
                    "quote",
                    "commitment",
                    "recap",
                    "brief",
                    "recovery",
                    "escalation",
                    "notification",
                }
            ):
                raise ValueError
            timestamp = datetime.fromisoformat(value[0])
            if timestamp.utcoffset() is None:
                raise ValueError
            return timestamp, UUID(value[1]), value[2]
        except (TypeError, ValueError, json.JSONDecodeError):
            from yuno_backend.volta.errors import InvalidDomainValue

            raise InvalidDomainValue("cursor", "malformed_cursor") from None

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

    @staticmethod
    async def _project_commitments(
        uow: OperationUnitOfWork,
        commitments: tuple[Commitment, ...],
    ) -> tuple[CommitmentProjection, ...]:
        projected: list[CommitmentProjection] = []
        for commitment in _ordered_commitment_history(commitments):
            evidence = await uow.evidence.get_by_commitment(commitment.id)
            if evidence is None:
                raise CommitmentEvidenceNotFound(commitment.id, commitment.evidence_id)
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
