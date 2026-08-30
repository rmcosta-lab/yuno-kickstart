"""Shared provider-neutral idempotency values for text-slice mutations."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from types import MappingProxyType
from uuid import UUID

from yuno_backend.volta.errors import InvalidDomainValue

__all__ = [
    "IdempotencyConflict",
    "IdempotencyResultMissing",
    "TextMutationIdempotency",
    "fingerprint",
    "validate_idempotency_key",
]


class IdempotencyConflict(RuntimeError):
    code = "idempotency_conflict"

    def __init__(self, resource_id: UUID, operation_name: str, key: str) -> None:
        del key
        self.resource_id = resource_id
        self.operation_id = resource_id
        self.operation_name = operation_name
        super().__init__(f"idempotency conflict: resource={resource_id} operation={operation_name}")


class IdempotencyResultMissing(RuntimeError):
    code = "idempotency_result_missing"

    def __init__(self, resource_id: UUID, operation_name: str) -> None:
        self.resource_id = resource_id
        self.operation_name = operation_name
        super().__init__(f"idempotency result missing: resource={resource_id}")


@dataclass(frozen=True, slots=True)
class TextMutationIdempotency:
    operation_name: str
    key: str
    fingerprint: str
    result_id: UUID
    created_at: datetime
    result_kind: str = "LEGACY_RESOURCE"
    result_snapshot: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        accepted_result_kinds = {
            "create_operation_draft": "LEGACY_RESOURCE",
            "approve_operation": "LEGACY_RESOURCE",
            "create_simulated_recap": "Recap",
            "create_call_brief": "CallBrief",
            "start_inbound_simulation": "RecoveryProjection",
            "replace_mandate": "OperationProjection",
            "create_escalation": "PostContactEscalation",
            "acknowledge_notification": "Notification",
        }
        if self.operation_name not in accepted_result_kinds:
            raise InvalidDomainValue("operation_name", "unsupported_text_mutation")
        validate_idempotency_key(self.key)
        if len(self.fingerprint) != 64 or any(
            char not in "0123456789abcdef" for char in self.fingerprint
        ):
            raise InvalidDomainValue("fingerprint", "sha256_hex_required")
        if not isinstance(self.result_id, UUID):
            raise InvalidDomainValue("result_id", "uuid_required")
        if not isinstance(self.created_at, datetime) or self.created_at.utcoffset() != timedelta(0):
            raise InvalidDomainValue("created_at", "aware_utc_required")
        if (
            not isinstance(self.result_kind, str)
            or not self.result_kind
            or len(self.result_kind) > 64
            or not self.result_kind.replace("_", "").isalnum()
        ):
            raise InvalidDomainValue("result_kind", "safe_code_required")
        if not isinstance(self.result_snapshot, Mapping):
            raise InvalidDomainValue("result_snapshot", "mapping_required")
        if self.result_kind != accepted_result_kinds[self.operation_name]:
            raise InvalidDomainValue("result_kind", "operation_result_kind_mismatch")
        object.__setattr__(self, "result_snapshot", _freeze_json(self.result_snapshot))


def _freeze_json(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze_json(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    return value


def validate_idempotency_key(key: str) -> None:
    if (
        not isinstance(key, str)
        or not 8 <= len(key) <= 128
        or not key.isascii()
        or not key.isprintable()
    ):
        raise InvalidDomainValue("idempotency_key", "printable_ascii_8_128_required")


def _canonical(value: object) -> object:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if hasattr(value, "__dataclass_fields__"):
        return _canonical(asdict(value))
    if isinstance(value, dict):
        return {key: _canonical(item) for key, item in value.items()}
    return value


def fingerprint(command: object, *, exclude: tuple[str, ...] = ()) -> str:
    values = asdict(command)  # type: ignore[arg-type]
    for excluded_field in exclude:
        values.pop(excluded_field, None)
    payload = json.dumps(_canonical(values), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()
