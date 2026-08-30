import stat
import wave
from datetime import UTC, datetime
from io import BytesIO
from types import SimpleNamespace
from uuid import UUID

import pytest
from yuno_backend.volta.errors import InvalidDomainValue
from yuno_backend.volta.evidence.models import AgreementEvidence
from yuno_backend.volta.evidence.playback import RetrieveEvidenceAudioService
from yuno_backend.volta.idempotency import TextMutationIdempotency
from yuno_backend.volta.negotiations.errors import InvalidNegotiationTransition
from yuno_backend.volta.recovery.fixtures import (
    DeterministicRecoveryFixtureCatalog,
)
from yuno_backend.volta.recovery.models import (
    RecoveryAttempt,
    RecoveryOutcome,
    RecoveryScenario,
)
from yuno_backend.volta.text_slice import (
    AuditQuery,
    TextNegotiationApplication,
    create_demo_evidence_storage,
)


@pytest.mark.parametrize("limit", [0, 101, True])
def test_audit_query_enforces_global_page_bound(limit: object) -> None:
    with pytest.raises(InvalidDomainValue):
        AuditQuery(UUID(int=1), limit=limit)  # type: ignore[arg-type]


def test_audit_cursor_round_trips_full_boundary_and_rejects_malformed() -> None:
    boundary = (datetime(2026, 9, 1, 12, tzinfo=UTC), UUID(int=2), "notification")
    cursor = TextNegotiationApplication._encode_cursor(boundary)
    assert TextNegotiationApplication._decode_cursor(cursor) == boundary
    with pytest.raises(InvalidDomainValue):
        TextNegotiationApplication._decode_cursor("not-a-valid-cursor")


def test_recovery_catalog_has_exactly_two_deterministic_scenarios() -> None:
    catalog = DeterministicRecoveryFixtureCatalog()
    safe = catalog.get(RecoveryScenario.MANDATE_SAFE)
    unsafe = catalog.get(RecoveryScenario.OUT_OF_MANDATE)
    assert safe.evidence is not None and safe.escalation_context is None
    assert unsafe.evidence is None and unsafe.escalation_context is not None


async def test_default_safe_fixture_is_retrievable_from_demo_storage(tmp_path) -> None:
    catalog = DeterministicRecoveryFixtureCatalog()
    evidence = catalog.get(RecoveryScenario.MANDATE_SAFE).evidence
    assert evidence is not None
    payload = await create_demo_evidence_storage(tmp_path).retrieve(
        evidence.recording_reference
    )
    assert payload[:4] == b"RIFF"
    assert payload[8:12] == b"WAVE"
    with wave.open(BytesIO(payload), "rb") as artifact:
        assert artifact.getnchannels() == 1
        assert artifact.getsampwidth() == 1
        assert artifact.getframerate() == 8_000
        assert artifact.getnframes() == 24_000
        duration_ms = artifact.getnframes() * 1_000 / artifact.getframerate()
        assert evidence.audio_start_ms < duration_ms


async def test_default_safe_fixture_passes_evidence_audio_retrieval(tmp_path) -> None:
    catalog = DeterministicRecoveryFixtureCatalog()
    fixture_evidence = catalog.get(RecoveryScenario.MANDATE_SAFE).evidence
    assert fixture_evidence is not None
    evidence_id = UUID(int=1701)
    stored_evidence = AgreementEvidence(
        evidence_id,
        UUID(int=1702),
        fixture_evidence.recording_reference,
        fixture_evidence.audio_start_ms,
        fixture_evidence.item_id,
        fixture_evidence.event_id,
        datetime(2026, 9, 1, 12, tzinfo=UTC),
    )

    class EvidenceRepository:
        async def get(self, requested_id: UUID) -> AgreementEvidence | None:
            return stored_evidence if requested_id == evidence_id else None

    class UnitOfWork:
        evidence = EvidenceRepository()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def rollback(self) -> None:
            return None

    storage = create_demo_evidence_storage(tmp_path)
    audio = await RetrieveEvidenceAudioService(UnitOfWork, storage).retrieve(
        evidence_id
    )

    assert audio.media_type == "audio/wav"
    assert audio.content_length == len(audio.content)
    assert audio.content[:4] == b"RIFF"
    assert audio.content[8:12] == b"WAVE"


@pytest.mark.parametrize("residual_payload", [b"", b"corrupt fixture"])
async def test_demo_storage_restores_empty_or_corrupt_recovery_fixture(
    tmp_path, residual_payload: bytes
) -> None:
    fixture = tmp_path / "fixture-recovery-mandate-safe.wav"
    fixture.write_bytes(residual_payload)
    fixture.chmod(0o644)

    catalog = DeterministicRecoveryFixtureCatalog()
    evidence = catalog.get(RecoveryScenario.MANDATE_SAFE).evidence
    assert evidence is not None
    payload = await create_demo_evidence_storage(tmp_path).retrieve(
        evidence.recording_reference
    )

    assert payload[:4] == b"RIFF"
    assert payload[8:12] == b"WAVE"
    assert stat.S_IMODE(fixture.stat().st_mode) == 0o600
    assert list(tmp_path.glob(".fixture-recovery-mandate-safe.wav.*.tmp")) == []


@pytest.mark.parametrize(
    ("operation_name", "result_kind"),
    [
        ("create_simulated_recap", "Recap"),
        ("create_call_brief", "CallBrief"),
        ("start_inbound_simulation", "RecoveryProjection"),
        ("replace_mandate", "OperationProjection"),
        ("create_escalation", "PostContactEscalation"),
        ("acknowledge_notification", "Notification"),
    ],
)
def test_all_f25_operations_accept_only_their_typed_snapshot_kind(
    operation_name: str, result_kind: str
) -> None:
    record = TextMutationIdempotency(
        operation_name,
        "phase25-contract-key",
        "a" * 64,
        UUID(int=1),
        datetime(2026, 9, 1, 12, tzinfo=UTC),
        result_kind,
        {"result_kind": result_kind},
    )
    assert record.result_snapshot["result_kind"] == result_kind
    with pytest.raises(InvalidDomainValue):
        TextMutationIdempotency(
            operation_name,
            "phase25-contract-key",
            "a" * 64,
            UUID(int=1),
            datetime(2026, 9, 1, 12, tzinfo=UTC),
            "WrongProjection",
            {},
        )


async def test_escalated_recovery_projection_rejects_missing_escalation() -> None:
    class MissingEscalations:
        async def get(self, escalation_id: UUID):
            return None

    attempt = RecoveryAttempt(
        UUID(int=1),
        UUID(int=2),
        UUID(int=3),
        RecoveryScenario.OUT_OF_MANDATE,
        4,
        5,
        "OUT_OF_MANDATE",
        RecoveryOutcome.ESCALATED,
        None,
        UUID(int=4),
        UUID(int=5),
        datetime(2026, 9, 1, 12, tzinfo=UTC),
    )
    uow = SimpleNamespace(post_contact_escalations=MissingEscalations())
    with pytest.raises(InvalidNegotiationTransition):
        await TextNegotiationApplication._project_recovery(uow, attempt)  # noqa: SLF001
