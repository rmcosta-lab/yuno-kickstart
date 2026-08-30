"""Provider-neutral outbound telephony application contract."""

from yuno_backend.volta.telephony.errors import (
    InvalidOutboundCallResponseError,
    OutboundCallAllowlistError,
    OutboundCallAuthenticationError,
    OutboundCallAuthorizationError,
    OutboundCallError,
    OutboundCallIdempotencyConflict,
    OutboundCallOutcomeUncertain,
    OutboundCallProviderError,
    OutboundCallRateLimitError,
    OutboundCallTimeoutError,
)
from yuno_backend.volta.telephony.gateway import OutboundCallGateway
from yuno_backend.volta.telephony.models import (
    OutboundCall,
    OutboundCallAttempt,
    OutboundCallAttemptReservation,
    OutboundCallAttemptState,
    OutboundCallAuthorization,
    OutboundCallFailure,
    OutboundCallFailureCategory,
    OutboundCallRequest,
    OutboundCallStatus,
    OutboundCallStatusEvent,
    OutboundCallUncertainReason,
    OutboundCallUncertainState,
    RecordingMode,
)
from yuno_backend.volta.telephony.repositories import OutboundCallAttemptStore
from yuno_backend.volta.telephony.services import (
    apply_status_event,
    outbound_call_request_fingerprint,
    transition_status,
)

__all__ = [
    "InvalidOutboundCallResponseError",
    "OutboundCall",
    "OutboundCallAllowlistError",
    "OutboundCallAttempt",
    "OutboundCallAttemptReservation",
    "OutboundCallAttemptState",
    "OutboundCallAttemptStore",
    "OutboundCallAuthenticationError",
    "OutboundCallAuthorization",
    "OutboundCallAuthorizationError",
    "OutboundCallError",
    "OutboundCallFailure",
    "OutboundCallFailureCategory",
    "OutboundCallGateway",
    "OutboundCallIdempotencyConflict",
    "OutboundCallOutcomeUncertain",
    "OutboundCallProviderError",
    "OutboundCallRateLimitError",
    "OutboundCallRequest",
    "OutboundCallStatus",
    "OutboundCallStatusEvent",
    "OutboundCallTimeoutError",
    "OutboundCallUncertainReason",
    "OutboundCallUncertainState",
    "RecordingMode",
    "apply_status_event",
    "outbound_call_request_fingerprint",
    "transition_status",
]
