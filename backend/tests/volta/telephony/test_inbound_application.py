from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
from yuno_backend.volta.mandates.models import OperationStatus
from yuno_backend.volta.recovery.models import RecoveryOutcome
from yuno_backend.volta.telephony import (
    AcceptInboundCallInput,
    CompleteInboundRecoveryInput,
    InboundCallApplication,
    InboundCallerBinding,
    InboundCallReplayConflict,
    InboundCallStateConflict,
    InboundCallStatus,
    InboundCorrelationAmbiguous,
    InboundCorrelationNotFound,
    RecordInboundConsentInput,
    StartInboundStreamInput,
)
from yuno_backend.volta.telephony import inbound as inbound_module


class Clock:
    def __init__(self) -> None:
        self.value = datetime(2026, 8, 30, 12, tzinfo=UTC)

    def now(self) -> datetime:
        return self.value


class Ids:
    def __init__(self) -> None:
        self.value = 100

    def new_id(self) -> UUID:
        self.value += 1
        return UUID(int=self.value)


class Attempts:
    def __init__(self) -> None:
        self.values = {}

    async def get_by_provider_call(self, provider_call_id, *, for_update=False):
        return self.values.get(provider_call_id)

    async def get_active_by_operation(self, operation_id, *, for_update=False):
        return next(
            (
                item
                for item in self.values.values()
                if item.operation_id == operation_id and item.status.active
            ),
            None,
        )

    async def add(self, attempt):
        self.values[attempt.provider_call_id] = attempt

    async def update(self, attempt):
        self.values[attempt.provider_call_id] = attempt


class Correlations:
    def __init__(self, values) -> None:
        self.values = values

    async def list_active_by_caller(self, caller_label, *, for_update=False):
        return tuple(
            item for item in self.values if item.caller_label == caller_label and item.active
        )

    async def add(self, binding):
        self.values.append(binding)


class Values:
    def __init__(self, value=None) -> None:
        self.value = value

    async def get(self, identifier, *, for_update=False):
        return self.value if self.value is not None and self.value.id == identifier else None

    async def get_active(self, operation_id):
        return self.value

    async def get_unresolved_by_operation(self, operation_id):
        return None


class UnresolvedEscalation:
    async def get_unresolved_by_operation(self, operation_id):
        return SimpleNamespace(id=UUID(int=999), operation_id=operation_id)


class Commitments:
    def __init__(self, active) -> None:
        self.active = active
        self.values = {active.id: active}

    async def get(self, identifier):
        return self.values.get(identifier)

    async def get_active(self, operation_id):
        return self.active


class Audit:
    def __init__(self) -> None:
        self.values = []

    async def add(self, event):
        self.values.append(event)


class Uow:
    def __init__(self, state) -> None:
        self.__dict__.update(state)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return None

    async def commit(self):
        return None

    async def rollback(self):
        return None


class Storage:
    def __init__(self) -> None:
        self.stores = 0
        self.deletes = 0

    async def store(self, commitment_id, payload):
        self.stores += 1
        return "stored/evidence.wav"

    async def retrieve(self, recording_reference):
        return b""

    async def delete(self, recording_reference):
        self.deletes += 1
        return None


def application(*, correlations=1):
    operation_id = UUID(int=1)
    call_id = UUID(int=2)
    commitment_id = UUID(int=3)
    operation = SimpleNamespace(
        id=operation_id,
        version=8,
        status=OperationStatus.COMMITTED,
        mandate=SimpleNamespace(version=2),
    )
    commitment = SimpleNamespace(
        id=commitment_id,
        operation_id=operation_id,
        call_id=call_id,
    )
    clock = Clock()
    bindings = [
        InboundCallerBinding(
            UUID(int=20 + index), "driver-demo", operation_id, True, clock.now()
        )
        for index in range(correlations)
    ]
    storage = Storage()
    state = {
        "operations": Values(operation),
        "commitments": Commitments(commitment),
        "post_contact_escalations": Values(),
        "audit_events": Audit(),
        "inbound_call_attempts": Attempts(),
        "inbound_caller_correlations": Correlations(bindings),
    }
    return (
        InboundCallApplication(lambda: Uow(state), storage, clock, Ids()),
        state,
        storage,
    )


@pytest.mark.asyncio
async def test_accept_consent_and_stream_are_bound_and_single_use() -> None:
    app, state, _ = application()
    accepted = await app.accept_inbound_call(
        AcceptInboundCallInput("driver-demo", "provider-call", UUID(int=10))
    )
    assert accepted.call_id == UUID(int=2)
    assert "+" not in repr(accepted)

    replay = await app.accept_inbound_call(
        AcceptInboundCallInput("driver-demo", "provider-call", UUID(int=10))
    )
    assert replay == accepted
    consented = await app.record_inbound_consent(
        RecordInboundConsentInput("provider-call", accepted.stream_binding)
    )
    assert consented == accepted
    streaming = await app.start_inbound_stream(
        StartInboundStreamInput("provider-call", accepted.stream_binding, "provider-stream")
    )
    assert streaming.status is InboundCallStatus.STREAMING
    duplicate = await app.start_inbound_stream(
        StartInboundStreamInput("provider-call", accepted.stream_binding, "provider-stream")
    )
    assert duplicate == streaming
    with pytest.raises(InboundCallStateConflict):
        await app.start_inbound_stream(
            StartInboundStreamInput(
                "provider-call", accepted.stream_binding, "provider-stream-replay"
            )
        )
    assert len(state["audit_events"].values) == 2


@pytest.mark.asyncio
async def test_correlation_and_changed_replay_fail_closed() -> None:
    missing, _, _ = application(correlations=0)
    with pytest.raises(InboundCorrelationNotFound):
        await missing.accept(
            AcceptInboundCallInput("driver-demo", "provider-call", UUID(int=10))
        )

    app, state, _ = application()
    accepted = await app.accept(
        AcceptInboundCallInput("driver-demo", "provider-call", UUID(int=10))
    )
    with pytest.raises(InboundCallReplayConflict):
        await app.record_consent(
            RecordInboundConsentInput("provider-call", "changed-binding")
        )
    attempt = state["inbound_call_attempts"].values["provider-call"]
    assert attempt.status is InboundCallStatus.AWAITING_CONSENT
    assert replace(attempt) == attempt
    assert accepted.stream_binding not in repr(attempt)


@pytest.mark.asyncio
async def test_ambiguous_correlation_fails_before_attempt_or_audit() -> None:
    app, state, _ = application(correlations=2)

    with pytest.raises(InboundCorrelationAmbiguous):
        await app.accept(
            AcceptInboundCallInput("driver-demo", "ambiguous-call", UUID(int=60))
        )

    assert state["inbound_call_attempts"].values == {}
    assert state["audit_events"].values == []


@pytest.mark.asyncio
@pytest.mark.parametrize("blocked_by", ["escalation", "active_attempt"])
async def test_ineligible_operation_fails_before_second_mutation(blocked_by: str) -> None:
    app, state, _ = application()
    if blocked_by == "escalation":
        state["post_contact_escalations"] = UnresolvedEscalation()
        expected_attempts = 0
        expected_audits = 0
    else:
        await app.accept(
            AcceptInboundCallInput("driver-demo", "existing-call", UUID(int=61))
        )
        expected_attempts = 1
        expected_audits = 1

    with pytest.raises(InboundCorrelationNotFound):
        await app.accept(
            AcceptInboundCallInput("driver-demo", "blocked-call", UUID(int=62))
        )

    assert len(state["inbound_call_attempts"].values) == expected_attempts
    assert len(state["audit_events"].values) == expected_audits
    assert "blocked-call" not in state["inbound_call_attempts"].values


@pytest.mark.asyncio
async def test_completion_replay_changed_replay_and_cleanup(monkeypatch) -> None:
    app, state, storage = application()
    binding = await app.accept(
        AcceptInboundCallInput("driver-demo", "provider-call", UUID(int=10))
    )
    await app.record_consent(
        RecordInboundConsentInput("provider-call", binding.stream_binding)
    )
    await app.start_stream(
        StartInboundStreamInput("provider-call", binding.stream_binding, "provider-stream")
    )
    resulting = SimpleNamespace(id=UUID(int=30), call_id=UUID(int=2))
    state["commitments"].values[resulting.id] = resulting
    recovery_calls = []
    brief_calls = []

    class RecoveryService:
        def __init__(self, *args):
            pass

        async def simulate_in_transaction(self, command):
            recovery_calls.append(command)
            return SimpleNamespace(
                id=UUID(int=31),
                outcome=RecoveryOutcome.REPLACED,
                resulting_commitment_id=resulting.id,
                resulting_evidence_id=UUID(int=32),
                after_operation_version=9,
            )

    class BriefService:
        def __init__(self, *args):
            pass

        async def generate_in_transaction(self, command):
            brief_calls.append(command)
            return SimpleNamespace(id=UUID(int=33))

    monkeypatch.setattr(inbound_module, "SimulateInboundRecoveryService", RecoveryService)
    monkeypatch.setattr(inbound_module, "GenerateBriefService", BriefService)
    command = CompleteInboundRecoveryInput(
        "provider-call",
        b"RIFF\x00\x00\x00\x00WAVEpost-consent",
        125,
        "agreement-item",
        "agreement-event",
        UUID(int=40),
    )
    completed = await app.complete(command)
    assert completed.status is InboundCallStatus.COMPLETED
    assert completed.resulting_commitment_id == resulting.id
    assert completed.resulting_evidence_id == UUID(int=32)
    assert completed.resulting_brief_id == UUID(int=33)
    assert len(recovery_calls) == len(brief_calls) == storage.stores == 1

    assert await app.complete(command) == completed
    assert len(recovery_calls) == len(brief_calls) == storage.stores == 1
    with pytest.raises(InboundCallReplayConflict):
        await app.complete(replace(command, event_id="changed-event"))
    assert len(recovery_calls) == len(brief_calls) == storage.stores == 1

    # A separate reserved attempt proves staged evidence cleanup on domain failure.
    failed_app, _, failed_storage = application()
    failed_binding = await failed_app.accept(
        AcceptInboundCallInput("driver-demo", "failed-call", UUID(int=50))
    )
    await failed_app.record_consent(
        RecordInboundConsentInput("failed-call", failed_binding.stream_binding)
    )

    class FailingRecoveryService:
        def __init__(self, *args):
            pass

        async def simulate_in_transaction(self, command):
            raise InboundCallStateConflict()

    monkeypatch.setattr(
        inbound_module, "SimulateInboundRecoveryService", FailingRecoveryService
    )
    with pytest.raises(InboundCallStateConflict):
        await failed_app.complete(replace(command, provider_call_id="failed-call"))
    assert failed_storage.stores == failed_storage.deletes == 1
