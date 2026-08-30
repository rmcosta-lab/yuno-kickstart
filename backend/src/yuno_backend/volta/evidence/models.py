"""Frozen provider-neutral values for recorded agreement evidence."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID

from yuno_backend.volta.errors import InvalidDomainValue
from yuno_backend.volta.mandates.models import Route

__all__ = ["AgreementEvidence", "CallBrief", "Recap", "RecapDisclosureState"]

_MAX_TEXT_LENGTH = 200


def _uuid(value: object, field: str) -> None:
    if not isinstance(value, UUID):
        raise InvalidDomainValue(field, "uuid_required")


def _version(value: object, field: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise InvalidDomainValue(field, "positive_integer_required")


def _utc(value: object, field: str) -> None:
    if not isinstance(value, datetime) or value.utcoffset() != timedelta(0):
        raise InvalidDomainValue(field, "aware_utc_required")


def _bounded_text(value: object, field: str) -> None:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > _MAX_TEXT_LENGTH
        or not value.isprintable()
    ):
        raise InvalidDomainValue(field, "bounded_printable_text_required")


class RecapDisclosureState(StrEnum):
    """The only disclosure state available in this phase.

    A future delivery-provider phase must add a new member (e.g. VERIFIED)
    rather than flip this value; there is no branch anywhere in this
    package that can construct a `Recap` with a different state.
    """

    SIMULATED = "SIMULATED"


@dataclass(frozen=True, slots=True)
class AgreementEvidence:
    id: UUID
    commitment_id: UUID
    recording_reference: str
    audio_start_ms: int
    item_id: str
    event_id: str
    created_at: datetime

    def __post_init__(self) -> None:
        _uuid(self.id, "id")
        _uuid(self.commitment_id, "commitment_id")
        _bounded_text(self.recording_reference, "recording_reference")
        if (
            not isinstance(self.audio_start_ms, int)
            or isinstance(self.audio_start_ms, bool)
            or self.audio_start_ms < 0
        ):
            raise InvalidDomainValue("audio_start_ms", "non_negative_integer_required")
        _bounded_text(self.item_id, "item_id")
        _bounded_text(self.event_id, "event_id")
        _utc(self.created_at, "created_at")


@dataclass(frozen=True, slots=True)
class CallBrief:
    id: UUID
    commitment_id: UUID
    operation_id: UUID
    route: Route
    carrier_id: UUID
    agreed_terms_reference: UUID
    mandate_version: int
    generated_at: datetime

    def __post_init__(self) -> None:
        uuid_fields = (
            "id",
            "commitment_id",
            "operation_id",
            "carrier_id",
            "agreed_terms_reference",
        )
        for field in uuid_fields:
            _uuid(getattr(self, field), field)
        if not isinstance(self.route, Route):
            raise InvalidDomainValue("route", "route_required")
        _version(self.mandate_version, "mandate_version")
        _utc(self.generated_at, "generated_at")


@dataclass(frozen=True, slots=True)
class Recap:
    id: UUID
    commitment_id: UUID
    operation_id: UUID
    disclosure_state: RecapDisclosureState
    generated_at: datetime

    def __post_init__(self) -> None:
        _uuid(self.id, "id")
        _uuid(self.commitment_id, "commitment_id")
        _uuid(self.operation_id, "operation_id")
        if not isinstance(self.disclosure_state, RecapDisclosureState):
            raise InvalidDomainValue("disclosure_state", "recap_disclosure_state_required")
        _utc(self.generated_at, "generated_at")
