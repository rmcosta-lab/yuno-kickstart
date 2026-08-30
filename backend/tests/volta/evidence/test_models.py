from datetime import UTC, datetime
from uuid import UUID

import pytest
from yuno_backend.volta.errors import InvalidDomainValue
from yuno_backend.volta.evidence import AgreementEvidence, CallBrief, Recap, RecapDisclosureState
from yuno_backend.volta.mandates import Route

NOW = datetime(2026, 9, 1, 12, tzinfo=UTC)


def _evidence(**overrides: object) -> AgreementEvidence:
    values: dict[str, object] = {
        "id": UUID(int=1),
        "commitment_id": UUID(int=2),
        "recording_reference": "recordings/2/abc.bin",
        "audio_start_ms": 0,
        "item_id": "item-1",
        "event_id": "event-1",
        "created_at": NOW,
    }
    values.update(overrides)
    return AgreementEvidence(**values)  # type: ignore[arg-type]


def test_agreement_evidence_accepts_valid_boundaries() -> None:
    evidence = _evidence(audio_start_ms=0)
    assert evidence.audio_start_ms == 0
    evidence = _evidence(audio_start_ms=999_999)
    assert evidence.audio_start_ms == 999_999


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("audio_start_ms", -1),
        ("audio_start_ms", True),
        ("recording_reference", ""),
        ("recording_reference", "   "),
        ("item_id", ""),
        ("event_id", ""),
    ],
)
def test_agreement_evidence_rejects_invalid_fields(field: str, value: object) -> None:
    with pytest.raises(InvalidDomainValue):
        _evidence(**{field: value})


def test_agreement_evidence_requires_aware_utc_created_at() -> None:
    with pytest.raises(InvalidDomainValue):
        _evidence(created_at=datetime(2026, 9, 1, 12))


def test_call_brief_requires_valid_fields() -> None:
    brief = CallBrief(
        UUID(int=1),
        UUID(int=2),
        UUID(int=3),
        Route("Port A", "Depot B"),
        UUID(int=4),
        UUID(int=5),
        1,
        NOW,
    )
    assert brief.mandate_version == 1
    with pytest.raises(InvalidDomainValue):
        CallBrief(
            UUID(int=1), UUID(int=2), UUID(int=3), Route("A", "B"), UUID(int=4), UUID(int=5), 0, NOW
        )


def test_recap_disclosure_state_has_exactly_one_member() -> None:
    assert list(RecapDisclosureState) == [RecapDisclosureState.SIMULATED]
    recap = Recap(UUID(int=1), UUID(int=2), UUID(int=3), RecapDisclosureState.SIMULATED, NOW)
    assert recap.disclosure_state is RecapDisclosureState.SIMULATED
    with pytest.raises(InvalidDomainValue):
        Recap(UUID(int=1), UUID(int=2), UUID(int=3), "SIMULATED", NOW)  # type: ignore[arg-type]
