"""Safe error response contract shared by all Volta routes."""

from enum import StrEnum
from uuid import UUID

from pydantic import Field

from app.schemas.common import PositiveVersion, ResponseModel, ShortText


class ApiErrorCode(StrEnum):
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    AUTHENTICATION_INVALID = "AUTHENTICATION_INVALID"
    ACTION_NOT_AUTHORIZED = "ACTION_NOT_AUTHORIZED"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    EVIDENCE_AUDIO_TOO_LARGE = "EVIDENCE_AUDIO_TOO_LARGE"
    STALE_OPERATION_VERSION = "STALE_OPERATION_VERSION"
    STALE_DRAFT_VERSION = "STALE_DRAFT_VERSION"
    IDEMPOTENCY_KEY_REUSED = "IDEMPOTENCY_KEY_REUSED"
    STATE_CONFLICT = "STATE_CONFLICT"
    MANDATE_CONFLICT = "MANDATE_CONFLICT"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    REALTIME_UNAVAILABLE = "REALTIME_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    CONTRACT_NOT_IMPLEMENTED = "CONTRACT_NOT_IMPLEMENTED"


class FieldIssue(ResponseModel):
    field: str = Field(min_length=1, max_length=500)
    message: ShortText
    code: str = Field(min_length=1, max_length=100)


class ApiErrorResponse(ResponseModel):
    code: ApiErrorCode
    message: ShortText
    request_id: str = Field(min_length=1, max_length=128)
    field_issues: list[FieldIssue] | None = None
    resource_id: UUID | None = None
    current_draft_version: PositiveVersion | None = None
    current_operation_version: PositiveVersion | None = None
