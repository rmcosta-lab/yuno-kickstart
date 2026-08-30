"""Immutable, bounded audit values independent of persistence and providers."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from types import MappingProxyType
from uuid import UUID

from yuno_backend.volta.errors import InvalidDomainValue

__all__ = ["AuditActorKind", "AuditEvent"]

type AuditMetadataScalar = str | int | bool | None
_SAFE_CODE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_SAFE_METADATA_KEY = re.compile(r"^[a-z][a-z0-9_]{0,49}$")
_MAX_METADATA_ITEMS = 20
_MAX_METADATA_STRING_LENGTH = 200
_MAX_METADATA_INTEGER = (2**53) - 1
_METADATA_SCHEMA_BY_EVENT = {
    "OPERATION_APPROVED": {"draft_version": int},
    "NEGOTIATION_STARTED": {},
    "PRE_CONTACT_ESCALATED": {},
    "QUOTE_RECORDED": {},
    "QUOTE_REJECTED": {},
    "COMMITMENT_ACTIVATED": {},
    "COMMITMENT_SUPERSEDED": {},
    "EVIDENCE_RECORDED": {},
    "BRIEF_GENERATED": {},
    "RECAP_GENERATED": {},
    "RECOVERY_REPLACEMENT_APPLIED": {},
    "POST_CONTACT_ESCALATED": {},
    "ESCALATION_RESUMED": {},
    "MANDATE_REPLACED": {},
    "ESCALATION_RESOLVED": {},
    "EXPLICIT_ESCALATION_CREATED": {},
    "NOTIFICATION_ACKNOWLEDGED": {},
    "HANDOFF_REQUESTED": {},
    "HANDOFF_JOINED": {},
    "HANDOFF_FAILED_SAFE": {},
    "HANDOFF_TIMED_OUT_SAFE": {},
}
_SENSITIVE_METADATA_TERMS = frozenset(
    {
        "audio",
        "authorization",
        "body",
        "contact",
        "credential",
        "cvv",
        "email",
        "header",
        "pan",
        "password",
        "payload",
        "phone",
        "prompt",
        "secret",
        "token",
    }
)


class AuditActorKind(StrEnum):
    COORDINATOR = "COORDINATOR"
    CARRIER_SIMULATOR = "CARRIER_SIMULATOR"
    SYSTEM = "SYSTEM"


def _validate_metadata(
    metadata: object,
    event_type: str,
) -> MappingProxyType[str, AuditMetadataScalar]:
    if not isinstance(metadata, Mapping):
        raise InvalidDomainValue("metadata", "mapping_required")
    if len(metadata) > _MAX_METADATA_ITEMS:
        raise InvalidDomainValue("metadata", "too_many_items")
    if event_type not in _METADATA_SCHEMA_BY_EVENT:
        raise InvalidDomainValue("event_type", "unsupported_event_type")
    safe: dict[str, AuditMetadataScalar] = {}
    accepted_fields = _METADATA_SCHEMA_BY_EVENT.get(event_type, {})
    for key, value in metadata.items():
        if not isinstance(key, str) or not _SAFE_METADATA_KEY.fullmatch(key):
            raise InvalidDomainValue("metadata", "unsafe_key")
        if any(term in key.split("_") for term in _SENSITIVE_METADATA_TERMS):
            raise InvalidDomainValue("metadata", "sensitive_key")
        if key not in accepted_fields:
            raise InvalidDomainValue("metadata", "unsupported_event_key")
        if type(value) not in (str, int, bool, type(None)):
            raise InvalidDomainValue("metadata", "safe_scalar_required")
        if type(value) is not accepted_fields[key]:
            raise InvalidDomainValue("metadata", "invalid_event_value_type")
        if isinstance(value, str) and len(value) > _MAX_METADATA_STRING_LENGTH:
            raise InvalidDomainValue("metadata", "string_too_long")
        if type(value) is int and not 0 <= value <= _MAX_METADATA_INTEGER:
            raise InvalidDomainValue("metadata", "integer_out_of_range")
        safe[key] = value
    return MappingProxyType(safe)


@dataclass(frozen=True, slots=True)
class AuditEvent:
    event_id: UUID
    operation_id: UUID
    operation_version: int
    actor_kind: AuditActorKind
    event_type: str
    occurred_at: datetime
    correlation_id: UUID
    metadata: Mapping[str, AuditMetadataScalar] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.event_id, UUID):
            raise InvalidDomainValue("event_id", "uuid_required")
        if not isinstance(self.operation_id, UUID):
            raise InvalidDomainValue("operation_id", "uuid_required")
        if (
            not isinstance(self.operation_version, int)
            or isinstance(self.operation_version, bool)
            or self.operation_version < 1
        ):
            raise InvalidDomainValue("operation_version", "positive_integer_required")
        if not isinstance(self.actor_kind, AuditActorKind):
            raise InvalidDomainValue("actor_kind", "audit_actor_kind_required")
        if not isinstance(self.event_type, str) or not _SAFE_CODE.fullmatch(self.event_type):
            raise InvalidDomainValue("event_type", "safe_code_required")
        if not isinstance(self.occurred_at, datetime) or self.occurred_at.utcoffset() != timedelta(
            0
        ):
            raise InvalidDomainValue("occurred_at", "aware_utc_required")
        if not isinstance(self.correlation_id, UUID):
            raise InvalidDomainValue("correlation_id", "uuid_required")
        object.__setattr__(self, "metadata", _validate_metadata(self.metadata, self.event_type))
