from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from yuno_backend.volta.evidence.storage.filesystem import FilesystemEvidenceStorage
from yuno_backend.volta.persistence import SqlAlchemyOperationUnitOfWork
from yuno_backend.volta.persistence.tables import _audit_events, _inbound_call_attempts
from yuno_backend.volta.recovery.commands import ReplacementEvidence
from yuno_backend.volta.recovery.errors import RecoveryScenarioMismatch
from yuno_backend.volta.recovery.fixtures import (
    DeterministicRecoveryFixtureCatalog,
    RecoveryFixture,
)
from yuno_backend.volta.recovery.models import EscalationContext, RecoveryScenario
from yuno_backend.volta.telephony import (
    AcceptInboundCallInput,
    CompleteInboundRecoveryInput,
    InboundCallApplication,
    InboundCallBinding,
    InboundCallerBinding,
    InboundCallReplayConflict,
    InboundCallStatus,
    InboundCorrelationNotFound,
    RecordInboundConsentInput,
    StartInboundStreamInput,
)

from .test_negotiation_repositories import _seed_winner

pytestmark = pytest.mark.asyncio
NOW = datetime(2026, 9, 2, 12, tzinfo=UTC)


class Clock:
    def now(self) -> datetime:
        return NOW


class Ids:
    def new_id(self) -> UUID:
        return uuid4()


class CountingStorage:
    def __init__(self, path: Path) -> None:
        self.delegate = FilesystemEvidenceStorage(path)
        self.stores = 0
        self.deletes = 0

    async def store(self, commitment_id: UUID, payload: bytes) -> str:
        self.stores += 1
        return await self.delegate.store(commitment_id, payload)

    async def retrieve(self, recording_reference: str) -> bytes:
        return await self.delegate.retrieve(recording_reference)

    async def delete(self, recording_reference: str) -> None:
        self.deletes += 1
        await self.delegate.delete(recording_reference)


def catalog(commitment, *, amount: Decimal) -> DeterministicRecoveryFixtureCatalog:
    return DeterministicRecoveryFixtureCatalog(
        (
            RecoveryFixture(
                RecoveryScenario.MANDATE_SAFE,
                replace(commitment.agreed_terms, amount=amount),
                "MANDATE_SAFE_REPLACEMENT",
                # Completion replaces this placeholder with staged evidence metadata.
                # The catalog still requires a correctly shaped safe fixture.
                ReplacementEvidence(
                    "placeholder.wav", 0, "placeholder-item", "placeholder-event"
                ),
                None,
            ),
            RecoveryFixture(
                RecoveryScenario.OUT_OF_MANDATE,
                replace(commitment.agreed_terms, amount=Decimal("999999")),
                "OUT_OF_MANDATE",
                None,
                EscalationContext(
                    "Replacement exceeds mandate.",
                    ("Keep the active commitment",),
                    "Request coordinator review.",
                ),
            ),
        )
    )


async def reserve_and_consent(
    app, operation_id: UUID, *, caller_label: str, provider_call_id: str
) -> tuple[str, str]:
    binding = await app.accept_inbound_call(
        AcceptInboundCallInput(caller_label, provider_call_id, UUID(int=9001))
    )
    await app.record_inbound_consent(
        RecordInboundConsentInput(provider_call_id, binding.stream_binding)
    )
    await app.start_inbound_stream(
        StartInboundStreamInput(
            provider_call_id, binding.stream_binding, f"{provider_call_id}-stream"
        )
    )
    assert binding.operation_id == operation_id
    return binding.provider_call_id, binding.stream_binding


async def test_completion_round_trip_replay_and_changed_replay(
    isolated_database_url: str, tmp_path: Path
) -> None:
    engine = create_async_engine(isolated_database_url, hide_parameters=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        operation_id, commitment = await _seed_winner(factory, 260000)
        async with SqlAlchemyOperationUnitOfWork(factory) as uow:
            await uow.inbound_caller_correlations.add(
                InboundCallerBinding(
                    uuid4(), "driver-demo-success", operation_id, True, NOW
                )
            )
            await uow.commit()
        storage = CountingStorage(tmp_path)
        app = InboundCallApplication(
            lambda: SqlAlchemyOperationUnitOfWork(factory),
            storage,
            Clock(),
            Ids(),
            catalog(commitment, amount=Decimal("900")),
        )
        await reserve_and_consent(
            app,
            operation_id,
            caller_label="driver-demo-success",
            provider_call_id="provider-call-success",
        )
        command = CompleteInboundRecoveryInput(
            "provider-call-success",
            b"RIFF\x00\x00\x00\x00WAVEpost-consent-evidence",
            125,
            "agreement-item",
            "agreement-event",
            UUID(int=9002),
        )
        completed = await app.complete_inbound_recovery(command)
        assert completed.status is InboundCallStatus.COMPLETED
        assert completed.resulting_commitment_id not in {None, commitment.id}
        assert completed.resulting_evidence_id is not None
        assert completed.resulting_brief_id is not None
        assert completed.recovery_attempt_id is not None
        assert storage.stores == 1

        replay = await InboundCallApplication(
            lambda: SqlAlchemyOperationUnitOfWork(factory),
            storage,
            Clock(),
            Ids(),
            catalog(commitment, amount=Decimal("900")),
        ).complete_inbound_recovery(command)
        assert replay == completed
        assert storage.stores == 1
        with pytest.raises(InboundCallReplayConflict):
            await app.complete_inbound_recovery(
                replace(command, item_id="changed-agreement-item")
            )
        assert storage.stores == 1

        async with SqlAlchemyOperationUnitOfWork(factory) as uow:
            durable = await uow.inbound_call_attempts.get_by_provider_call(
                "provider-call-success"
            )
            brief = await uow.briefs.get(completed.resulting_brief_id)
            recovery = await uow.recovery_attempts.get(completed.recovery_attempt_id)
            active = await uow.commitments.get_active(operation_id)
            await uow.rollback()
        assert durable == completed
        assert brief is not None and brief.commitment_id == completed.resulting_commitment_id
        assert recovery is not None
        assert recovery.resulting_evidence_id == completed.resulting_evidence_id
        assert active is not None and active.id == completed.resulting_commitment_id
    finally:
        await engine.dispose()


async def test_failed_completion_rolls_back_and_deletes_staged_evidence(
    isolated_database_url: str, tmp_path: Path
) -> None:
    engine = create_async_engine(isolated_database_url, hide_parameters=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        operation_id, commitment = await _seed_winner(factory, 261000)
        async with SqlAlchemyOperationUnitOfWork(factory) as uow:
            await uow.inbound_caller_correlations.add(
                InboundCallerBinding(
                    uuid4(), "driver-demo-rollback", operation_id, True, NOW
                )
            )
            await uow.commit()
        storage = CountingStorage(tmp_path)
        app = InboundCallApplication(
            lambda: SqlAlchemyOperationUnitOfWork(factory),
            storage,
            Clock(),
            Ids(),
            catalog(commitment, amount=Decimal("999999")),
        )
        await reserve_and_consent(
            app,
            operation_id,
            caller_label="driver-demo-rollback",
            provider_call_id="provider-call-rollback",
        )
        with pytest.raises(RecoveryScenarioMismatch):
            await app.complete_inbound_recovery(
                CompleteInboundRecoveryInput(
                    "provider-call-rollback",
                    b"RIFF\x00\x00\x00\x00WAVEpost-consent-evidence",
                    125,
                    "agreement-item",
                    "agreement-event",
                    UUID(int=9010),
                )
            )
        assert storage.stores == 1
        assert storage.deletes == 1
        artifacts = await asyncio.to_thread(lambda: tuple(tmp_path.rglob("*.wav")))
        assert not artifacts
        async with SqlAlchemyOperationUnitOfWork(factory) as uow:
            durable = await uow.inbound_call_attempts.get_by_provider_call(
                "provider-call-rollback"
            )
            active = await uow.commitments.get_active(operation_id)
            await uow.rollback()
        assert durable is not None and durable.status is InboundCallStatus.STREAMING
        assert active is not None and active.id == commitment.id
    finally:
        await engine.dispose()


async def test_concurrent_active_reservations_leave_one_durable_attempt(
    isolated_database_url: str, tmp_path: Path
) -> None:
    engine = create_async_engine(isolated_database_url, hide_parameters=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        operation_id, commitment = await _seed_winner(factory, 262000)
        caller_label = "driver-demo-concurrent"
        async with SqlAlchemyOperationUnitOfWork(factory) as uow:
            await uow.inbound_caller_correlations.add(
                InboundCallerBinding(uuid4(), caller_label, operation_id, True, NOW)
            )
            await uow.commit()
        app = InboundCallApplication(
            lambda: SqlAlchemyOperationUnitOfWork(factory),
            CountingStorage(tmp_path),
            Clock(),
            Ids(),
            catalog(commitment, amount=Decimal("900")),
        )

        async def reserve(provider_call_id: str):
            try:
                return await app.accept_inbound_call(
                    AcceptInboundCallInput(caller_label, provider_call_id, uuid4())
                )
            except Exception as error:
                return error

        results = await asyncio.gather(
            reserve("provider-call-concurrent-a"),
            reserve("provider-call-concurrent-b"),
        )
        bindings = [item for item in results if isinstance(item, InboundCallBinding)]
        failures = [item for item in results if isinstance(item, Exception)]
        assert len(bindings) == 1
        assert len(failures) == 1
        assert isinstance(failures[0], InboundCorrelationNotFound)

        winner = bindings[0]
        duplicate = await app.accept_inbound_call(
            AcceptInboundCallInput(caller_label, winner.provider_call_id, uuid4())
        )
        assert duplicate == winner

        async with factory() as session:
            active_count = (
                await session.execute(
                    select(func.count())
                    .select_from(_inbound_call_attempts)
                    .where(
                        _inbound_call_attempts.c.operation_id == operation_id,
                        _inbound_call_attempts.c.status.in_(
                            ("AWAITING_CONSENT", "CONSENTED", "STREAMING")
                        ),
                    )
                )
            ).scalar_one()
            audit_count = (
                await session.execute(
                    select(func.count())
                    .select_from(_audit_events)
                    .where(
                        _audit_events.c.operation_id == operation_id,
                        _audit_events.c.event_type == "INBOUND_CALL_ACCEPTED",
                    )
                )
            ).scalar_one()
        assert active_count == 1
        assert audit_count == 1
    finally:
        await engine.dispose()
