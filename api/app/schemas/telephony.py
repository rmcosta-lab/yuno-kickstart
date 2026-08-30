"""Public provider-neutral telephony contracts."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field

from app.schemas.common import (
    PositiveVersion,
    ResponseModel,
    SafeIdentifier,
    StrictRequestModel,
    UtcTimestamp,
)

HandoffContextText = Annotated[str, Field(min_length=1, max_length=300)]


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


class RequestHumanHandoffRequest(StrictRequestModel):
    coordinator_destination_label: SafeIdentifier
    authorized_by: SafeIdentifier
    authorized_at: UtcTimestamp
    expected_call_status_updated_at: UtcTimestamp


class HumanHandoffContextResponse(ResponseModel):
    mandate_version: PositiveVersion
    mandate_facts: list[HandoffContextText] = Field(max_length=20)
    eligible_quote_summaries: list[HandoffContextText] = Field(max_length=20)
    structured_call_brief: list[HandoffContextText] = Field(max_length=20)
    call_status: SafeIdentifier


class HumanHandoffResponse(ResponseModel):
    handoff_id: UUID
    call_id: UUID
    status: Literal["CONNECTING", "JOINED", "FAILED_SAFE", "TIMED_OUT_SAFE"]
    requested_at: UtcTimestamp
    status_updated_at: UtcTimestamp
    context: HumanHandoffContextResponse


class HumanHandoffReadinessResponse(ResponseModel):
    call_id: UUID
    call_status_updated_at: UtcTimestamp
    context: HumanHandoffContextResponse
