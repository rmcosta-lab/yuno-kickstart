from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta

import pytest
from yuno_backend.volta.errors import InvalidDomainValue
from yuno_backend.volta.telephony import (
    OutboundCall,
    OutboundCallError,
    OutboundCallStatus,
    OutboundCallStatusEvent,
    apply_status_event,
    transition_status,
)


def _event(
    call: OutboundCall,
    fixed_now: datetime,
    *,
    event_id: str,
    sequence: int,
    status: OutboundCallStatus,
) -> OutboundCallStatusEvent:
    return OutboundCallStatusEvent(
        provider_event_id=event_id,
        provider_call_id=call.provider_call_id,
        status=status,
        sequence_number=sequence,
        observed_at=fixed_now + timedelta(seconds=sequence + 1),
    )


def test_status_progression_uses_sequence_not_arrival_order(
    outbound_call: OutboundCall, fixed_now: datetime
) -> None:
    ringing = apply_status_event(
        outbound_call,
        _event(
            outbound_call,
            fixed_now,
            event_id="event.ringing",
            sequence=2,
            status=OutboundCallStatus.RINGING,
        ),
    )
    old_initiated = apply_status_event(
        ringing,
        _event(
            outbound_call,
            fixed_now,
            event_id="event.initiated",
            sequence=1,
            status=OutboundCallStatus.INITIATED,
        ),
    )
    duplicate = apply_status_event(
        ringing,
        _event(
            outbound_call,
            fixed_now,
            event_id="event.ringing",
            sequence=3,
            status=OutboundCallStatus.FAILED,
        ),
    )

    assert ringing.status is OutboundCallStatus.RINGING
    assert ringing.last_status_sequence_number == 2
    assert old_initiated is ringing
    assert duplicate is ringing


def test_non_latest_duplicate_event_id_is_ignored_even_with_newer_sequence(
    outbound_call: OutboundCall, fixed_now: datetime
) -> None:
    initiated = apply_status_event(
        outbound_call,
        _event(
            outbound_call,
            fixed_now,
            event_id="event.first",
            sequence=1,
            status=OutboundCallStatus.INITIATED,
        ),
    )
    ringing = apply_status_event(
        initiated,
        _event(
            outbound_call,
            fixed_now,
            event_id="event.second",
            sequence=2,
            status=OutboundCallStatus.RINGING,
        ),
    )
    duplicate_first = apply_status_event(
        ringing,
        _event(
            outbound_call,
            fixed_now,
            event_id="event.first",
            sequence=9,
            status=OutboundCallStatus.FAILED,
        ),
    )
    assert duplicate_first is ringing


@pytest.mark.parametrize(
    "terminal",
    [status for status in OutboundCallStatus if status.is_terminal],
)
def test_terminal_status_never_regresses_or_changes_outcome(
    outbound_call: OutboundCall,
    fixed_now: datetime,
    terminal: OutboundCallStatus,
) -> None:
    terminal_call = apply_status_event(
        outbound_call,
        _event(
            outbound_call,
            fixed_now,
            event_id="event.terminal",
            sequence=3,
            status=terminal,
        ),
    )
    changed = apply_status_event(
        terminal_call,
        _event(
            outbound_call,
            fixed_now,
            event_id="event.later",
            sequence=4,
            status=(
                OutboundCallStatus.COMPLETED
                if terminal is not OutboundCallStatus.COMPLETED
                else OutboundCallStatus.FAILED
            ),
        ),
    )

    assert changed.status is terminal
    assert changed.last_status_sequence_number == 4


def test_newer_regressive_nonterminal_event_advances_cursor_only(
    outbound_call: OutboundCall, fixed_now: datetime
) -> None:
    in_progress = apply_status_event(
        outbound_call,
        _event(
            outbound_call,
            fixed_now,
            event_id="event.active",
            sequence=2,
            status=OutboundCallStatus.IN_PROGRESS,
        ),
    )
    regressive = apply_status_event(
        in_progress,
        _event(
            outbound_call,
            fixed_now,
            event_id="event.queued-late",
            sequence=3,
            status=OutboundCallStatus.QUEUED,
        ),
    )
    assert regressive.status is OutboundCallStatus.IN_PROGRESS
    assert regressive.last_status_sequence_number == 3
    assert regressive.status_updated_at == in_progress.status_updated_at


def test_higher_sequence_cannot_regress_status_timestamp(
    outbound_call: OutboundCall, fixed_now: datetime
) -> None:
    first = apply_status_event(
        outbound_call,
        _event(
            outbound_call,
            fixed_now,
            event_id="event.ringing",
            sequence=10,
            status=OutboundCallStatus.RINGING,
        ),
    )
    older_observation = OutboundCallStatusEvent(
        provider_event_id="event.active",
        provider_call_id=outbound_call.provider_call_id,
        status=OutboundCallStatus.IN_PROGRESS,
        sequence_number=11,
        observed_at=fixed_now + timedelta(seconds=2),
    )
    progressed = apply_status_event(first, older_observation)
    assert progressed.status is OutboundCallStatus.IN_PROGRESS
    assert progressed.status_updated_at == first.status_updated_at


def test_status_helper_rejects_cross_call_event(
    outbound_call: OutboundCall, fixed_now: datetime
) -> None:
    event = replace(
        _event(
            outbound_call,
            fixed_now,
            event_id="event.other",
            sequence=1,
            status=OutboundCallStatus.RINGING,
        ),
        provider_call_id="provider.call.other",
    )
    with pytest.raises(InvalidDomainValue, match="must_match"):
        apply_status_event(outbound_call, event)


def test_transition_status_is_monotonic() -> None:
    assert (
        transition_status(OutboundCallStatus.RINGING, OutboundCallStatus.QUEUED)
        is OutboundCallStatus.RINGING
    )
    assert (
        transition_status(OutboundCallStatus.RINGING, OutboundCallStatus.IN_PROGRESS)
        is OutboundCallStatus.IN_PROGRESS
    )
    assert (
        transition_status(OutboundCallStatus.FAILED, OutboundCallStatus.COMPLETED)
        is OutboundCallStatus.FAILED
    )


def test_errors_expose_only_allowlisted_bounded_metadata() -> None:
    error = OutboundCallError(
        destination_label="unsafe private destination",
        provider_request_id="request.safe",
        retry_after_seconds=999_999,
    )
    assert str(error) == "outbound_call"
    assert dict(error.safe_metadata) == {
        "category": "outbound_call",
        "call_session_id": None,
        "destination_label": None,
        "provider_request_id": "request.safe",
        "retry_after_seconds": 86_400,
    }
    assert "unsafe private destination" not in repr(error)


@pytest.mark.parametrize("sequence", [-1, True, 1.5])
def test_status_event_requires_non_negative_integer_sequence(
    outbound_call: OutboundCall, fixed_now: datetime, sequence: object
) -> None:
    with pytest.raises(InvalidDomainValue, match="non_negative"):
        OutboundCallStatusEvent(
            provider_event_id="event.safe",
            provider_call_id=outbound_call.provider_call_id,
            status=OutboundCallStatus.RINGING,
            sequence_number=sequence,  # type: ignore[arg-type]
            observed_at=fixed_now,
        )
