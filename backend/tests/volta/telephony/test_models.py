from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from yuno_backend.volta.errors import InvalidDomainValue
from yuno_backend.volta.telephony import (
    OutboundCall,
    OutboundCallAttempt,
    OutboundCallAttemptReservation,
    OutboundCallAttemptState,
    OutboundCallAuthorization,
    OutboundCallFailure,
    OutboundCallFailureCategory,
    OutboundCallRequest,
    OutboundCallUncertainReason,
    OutboundCallUncertainState,
    RecordingMode,
    outbound_call_request_fingerprint,
)


def test_request_is_immutable_bounded_and_contains_no_destination_number(
    call_request: OutboundCallRequest,
) -> None:
    assert "phone" not in call_request.__dataclass_fields__
    assert "provider" not in call_request.__dataclass_fields__
    assert "+" not in repr(call_request)
    with pytest.raises((AttributeError, TypeError)):
        call_request.destination_label = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    "values",
    [
        {"actor_id": "unsafe actor"},
        {"authorized_at": datetime(2026, 8, 30, 12, 0)},
        {"ai_disclosure_required": False},
        {
            "recording_mode": RecordingMode.AFTER_EXPLICIT_CONSENT,
            "recording_consent_required": False,
        },
        {
            "recording_mode": RecordingMode.DISABLED,
            "recording_consent_required": True,
        },
    ],
)
def test_authorization_fails_closed(values: dict[str, object], fixed_now: datetime) -> None:
    defaults: dict[str, object] = {
        "actor_id": "operator.demo",
        "authorized_at": fixed_now,
    }
    defaults.update(values)
    with pytest.raises(InvalidDomainValue):
        OutboundCallAuthorization(**defaults)  # type: ignore[arg-type]


def test_recording_can_only_start_after_explicit_consent(fixed_now: datetime) -> None:
    authorization = OutboundCallAuthorization(
        actor_id="operator.demo",
        authorized_at=fixed_now,
        recording_mode=RecordingMode.AFTER_EXPLICIT_CONSENT,
        recording_consent_required=True,
    )
    assert authorization.recording_mode is RecordingMode.AFTER_EXPLICIT_CONSENT
    assert authorization.recording_consent_required is True


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("idempotency_key", "short"),
        ("destination_label", "+not-a-label"),
        ("destination_label", "carrier private"),
        ("destination_label", "x" * 129),
    ],
)
def test_request_rejects_unsafe_strings(
    call_request: OutboundCallRequest, field_name: str, value: str
) -> None:
    with pytest.raises(InvalidDomainValue):
        replace(call_request, **{field_name: value})


def test_fingerprint_is_stable_and_excludes_only_idempotency_key(
    call_request: OutboundCallRequest,
) -> None:
    original = outbound_call_request_fingerprint(call_request)
    replay = replace(call_request, idempotency_key="different-replay-key")
    changed_destination = replace(call_request, destination_label="carrier.demo.secondary")

    assert len(original) == 64
    assert outbound_call_request_fingerprint(replay) == original
    assert outbound_call_request_fingerprint(changed_destination) != original


@pytest.mark.parametrize("state", list(OutboundCallAttemptState))
def test_attempt_requires_payload_matching_state(
    state: OutboundCallAttemptState,
    call_request: OutboundCallRequest,
    outbound_call: OutboundCall,
    fixed_now: datetime,
) -> None:
    uncertainty = OutboundCallUncertainState(
        reason=OutboundCallUncertainReason.TIMEOUT,
        occurred_at=fixed_now,
    )
    valid_result = outbound_call if state is OutboundCallAttemptState.SUCCEEDED else None
    valid_uncertainty = (
        uncertainty if state is OutboundCallAttemptState.UNCERTAIN else None
    )
    failure = OutboundCallFailure(
        category=OutboundCallFailureCategory.PROVIDER_REJECTED,
        occurred_at=fixed_now,
        status_code=422,
    )
    valid_failure = failure if state is OutboundCallAttemptState.FAILED else None
    attempt = OutboundCallAttempt(
        operation_id=call_request.operation_id,
        idempotency_key=call_request.idempotency_key,
        request_fingerprint="f" * 64,
        state=state,
        result=valid_result,
        uncertainty=valid_uncertainty,
        failure=valid_failure,
        created_at=fixed_now,
        updated_at=fixed_now,
    )
    assert attempt.state is state

    with pytest.raises(InvalidDomainValue, match="attempt_payload"):
        replace(attempt, result=outbound_call, uncertainty=uncertainty)


def test_attempt_rejects_bad_digest_and_time_order(
    call_request: OutboundCallRequest, fixed_now: datetime
) -> None:
    kwargs = {
        "operation_id": call_request.operation_id,
        "idempotency_key": call_request.idempotency_key,
        "request_fingerprint": "f" * 64,
        "state": OutboundCallAttemptState.PENDING,
        "result": None,
        "uncertainty": None,
        "failure": None,
        "created_at": fixed_now,
        "updated_at": fixed_now,
    }
    with pytest.raises(InvalidDomainValue, match="request_fingerprint"):
        OutboundCallAttempt(**{**kwargs, "request_fingerprint": "not-a-digest"})
    with pytest.raises(InvalidDomainValue, match="updated_at"):
        OutboundCallAttempt(
            **{**kwargs, "updated_at": fixed_now - timedelta(microseconds=1)}
        )


def test_new_reservation_must_be_pending(
    call_request: OutboundCallRequest,
    outbound_call: OutboundCall,
    fixed_now: datetime,
) -> None:
    succeeded = OutboundCallAttempt(
        operation_id=call_request.operation_id,
        idempotency_key=call_request.idempotency_key,
        request_fingerprint="f" * 64,
        state=OutboundCallAttemptState.SUCCEEDED,
        result=outbound_call,
        uncertainty=None,
        failure=None,
        created_at=fixed_now,
        updated_at=fixed_now,
    )
    with pytest.raises(InvalidDomainValue, match="new_reservation"):
        OutboundCallAttemptReservation(attempt=succeeded, created=True)


@pytest.mark.parametrize("status_code", [99, 600, True, "401"])
def test_definitive_failure_has_bounded_safe_status(
    fixed_now: datetime, status_code: object
) -> None:
    with pytest.raises(InvalidDomainValue, match="status_code"):
        OutboundCallFailure(
            category=OutboundCallFailureCategory.AUTHENTICATION,
            occurred_at=fixed_now,
            status_code=status_code,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("category", list(OutboundCallFailureCategory))
def test_each_definitive_failure_category_is_a_safe_durable_value(
    fixed_now: datetime, category: OutboundCallFailureCategory
) -> None:
    failure = OutboundCallFailure(category=category, occurred_at=fixed_now)
    assert failure.category is category
    assert failure.status_code is None


def test_outbound_call_cursor_is_complete_and_bounded(
    outbound_call: OutboundCall,
) -> None:
    with pytest.raises(InvalidDomainValue, match="complete_cursor"):
        replace(outbound_call, last_status_event_id="event.safe")
    with pytest.raises(InvalidDomainValue, match="non_negative"):
        replace(
            outbound_call,
            last_status_event_id="event.safe",
            last_status_sequence_number=-1,
        )
    with pytest.raises(InvalidDomainValue, match="unique_bounded"):
        replace(
            outbound_call,
            last_status_event_id="event.safe",
            last_status_sequence_number=1,
            processed_status_event_ids=("event.safe", "event.safe"),
        )


def test_utc_validation_accepts_only_aware_utc(fixed_now: datetime) -> None:
    offset_time = fixed_now.astimezone(UTC) + timedelta(0)
    assert offset_time.utcoffset() == timedelta(0)
    with pytest.raises(InvalidDomainValue, match="aware_utc"):
        OutboundCallAuthorization(
            actor_id="operator.demo", authorized_at=fixed_now.replace(tzinfo=None)
        )


def test_uuid_fields_reject_string_values(
    call_request: OutboundCallRequest,
) -> None:
    with pytest.raises(InvalidDomainValue, match="uuid_required"):
        replace(call_request, operation_id=str(UUID(int=1)))  # type: ignore[arg-type]
