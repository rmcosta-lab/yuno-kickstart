from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from types import MappingProxyType
from uuid import UUID

import pytest
from yuno_backend.volta.audit import AuditActorKind, AuditEvent
from yuno_backend.volta.mandates import InvalidDomainValue


def event(**changes: object) -> AuditEvent:
    values: dict[str, object] = {
        "event_id": UUID(int=601),
        "operation_id": UUID(int=602),
        "operation_version": 1,
        "actor_kind": AuditActorKind.COORDINATOR,
        "event_type": "OPERATION_APPROVED",
        "occurred_at": datetime(2026, 9, 1, tzinfo=UTC),
        "correlation_id": UUID(int=603),
        "metadata": {"draft_version": 1},
    }
    values.update(changes)
    return AuditEvent(**values)  # type: ignore[arg-type]


def test_event_is_frozen_and_metadata_is_a_defensive_immutable_copy() -> None:
    submitted = {"draft_version": 1}
    audit_event = event(metadata=submitted)
    submitted["draft_version"] = 2

    assert audit_event.metadata == {"draft_version": 1}
    assert isinstance(audit_event.metadata, MappingProxyType)
    with pytest.raises(TypeError):
        audit_event.metadata["draft_version"] = 2  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        audit_event.event_type = "CHANGED"  # type: ignore[misc]


@pytest.mark.parametrize(
    "metadata",
    [
        {"authorization_header": "hidden"},
        {"raw_provider_payload": "hidden"},
        {"source_prompt": "hidden"},
        {"private_audio": "hidden"},
        {"participant_contact": "hidden"},
        {"access_token": "hidden"},
        {"draft_version": 2**53},
        {"draft_version": -1},
        {"reason": "Bearer synthetic-secret"},
        {"draft_version": [1]},
        {"draft_version": "x" * 201},
        {f"key_{index}": index for index in range(21)},
    ],
)
def test_metadata_rejects_sensitive_unbounded_or_nested_values(
    metadata: dict[str, object],
) -> None:
    with pytest.raises(InvalidDomainValue):
        event(metadata=metadata)
