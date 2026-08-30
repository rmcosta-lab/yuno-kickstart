"""Public provider-neutral outbound-call contract."""

from typing import Literal
from uuid import UUID

from pydantic import Field

from app.schemas.common import ResponseModel, SafeIdentifier, StrictRequestModel, UtcTimestamp


class CreateOutboundCallRequest(StrictRequestModel):
    call_session_id: UUID
    destination_label: SafeIdentifier
    authorized_by: SafeIdentifier
    authorized_at: UtcTimestamp
    ai_disclosure_required: Literal[True]
    recording_mode: Literal["DISABLED"]
    recording_consent_required: Literal[False]


class OutboundCallResponse(ResponseModel):
    call_session_id: UUID
    provider_call_id: str = Field(min_length=1, max_length=128)
    status: Literal[
        "QUEUED",
        "INITIATED",
        "RINGING",
        "IN_PROGRESS",
        "COMPLETED",
        "BUSY",
        "FAILED",
        "NO_ANSWER",
        "CANCELED",
    ]
    created_at: UtcTimestamp
    status_updated_at: UtcTimestamp
