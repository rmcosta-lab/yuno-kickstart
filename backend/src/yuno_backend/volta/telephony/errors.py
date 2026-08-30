"""Safe provider-neutral failures for outbound telephony."""

from __future__ import annotations

import re
from types import MappingProxyType
from typing import ClassVar
from uuid import UUID

__all__ = [
    "HumanHandoffActiveConflict",
    "HumanHandoffAuthenticationError",
    "HumanHandoffAuthorityError",
    "HumanHandoffCallNotLiveError",
    "HumanHandoffDestinationError",
    "HumanHandoffError",
    "HumanHandoffIdempotencyConflict",
    "HumanHandoffMissingContextError",
    "HumanHandoffNotFoundError",
    "HumanHandoffOutcomeUncertain",
    "HumanHandoffPermissionError",
    "HumanHandoffProviderError",
    "HumanHandoffRateLimitError",
    "HumanHandoffStaleCallError",
    "HumanHandoffTimeoutError",
    "InboundCallError",
    "InboundCallerNotAllowed",
    "InboundCorrelationNotFound",
    "InboundCorrelationAmbiguous",
    "InboundCallReplayConflict",
    "InboundConsentRequired",
    "InboundCallStateConflict",
    "InvalidOutboundCallResponseError",
    "OutboundCallAllowlistError",
    "OutboundCallAuthenticationError",
    "OutboundCallAuthorizationError",
    "OutboundCallError",
    "OutboundCallIdempotencyConflict",
    "OutboundCallOutcomeUncertain",
    "OutboundCallProviderError",
    "OutboundCallRateLimitError",
    "OutboundCallTimeoutError",
]


class InboundCallError(RuntimeError):
    """Safe inbound failure without provider, caller, or database details."""

    code = "inbound_call_error"

    def __init__(self) -> None:
        super().__init__(self.code)


class InboundCallerNotAllowed(InboundCallError):
    code = "inbound_caller_not_allowed"


class InboundCorrelationNotFound(InboundCallError):
    code = "inbound_correlation_not_found"


class InboundCorrelationAmbiguous(InboundCallError):
    code = "inbound_correlation_ambiguous"


class InboundCallReplayConflict(InboundCallError):
    code = "inbound_call_replay_conflict"


class InboundConsentRequired(InboundCallError):
    code = "inbound_consent_required"


class InboundCallStateConflict(InboundCallError):
    code = "inbound_call_state_conflict"

_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")


def _safe_identifier(value: object) -> str | None:
    return value if isinstance(value, str) and _SAFE_IDENTIFIER.fullmatch(value) else None


class HumanHandoffError(RuntimeError):
    """Safe application failure without participant or provider details."""

    category: ClassVar[str] = "human_handoff"

    def __init__(self, *, call_id: UUID | None = None) -> None:
        self.call_id = call_id if isinstance(call_id, UUID) else None
        super().__init__(self.category)

    @property
    def safe_metadata(self) -> MappingProxyType[str, str | None]:
        return MappingProxyType(
            {
                "category": self.category,
                "call_id": str(self.call_id) if self.call_id is not None else None,
            }
        )


class HumanHandoffCallNotLiveError(HumanHandoffError):
    category = "call_not_live"


class HumanHandoffStaleCallError(HumanHandoffError):
    category = "stale_call"


class HumanHandoffMissingContextError(HumanHandoffError):
    category = "missing_context"


class HumanHandoffDestinationError(HumanHandoffError):
    category = "unknown_destination"


class HumanHandoffActiveConflict(HumanHandoffError):
    category = "active_handoff"


class HumanHandoffIdempotencyConflict(HumanHandoffError):
    category = "idempotency_conflict"


class HumanHandoffAuthorityError(HumanHandoffError):
    category = "ai_authority_revoked"


class HumanHandoffAuthenticationError(HumanHandoffError):
    category = "authentication"


class HumanHandoffPermissionError(HumanHandoffError):
    category = "permission"


class HumanHandoffRateLimitError(HumanHandoffError):
    category = "rate_limit"


class HumanHandoffProviderError(HumanHandoffError):
    category = "provider"


class HumanHandoffTimeoutError(HumanHandoffError):
    category = "timeout"


class HumanHandoffOutcomeUncertain(HumanHandoffError):
    category = "uncertain_outcome"


class HumanHandoffNotFoundError(HumanHandoffError):
    category = "not_found"


class OutboundCallError(RuntimeError):
    """Base failure exposing only bounded operational diagnostics."""

    category: ClassVar[str] = "outbound_call"

    def __init__(
        self,
        *,
        call_session_id: UUID | None = None,
        destination_label: str | None = None,
        provider_request_id: str | None = None,
        retry_after_seconds: int | None = None,
    ) -> None:
        self.call_session_id = call_session_id if isinstance(call_session_id, UUID) else None
        self.destination_label = _safe_identifier(destination_label)
        self.provider_request_id = _safe_identifier(provider_request_id)
        self.retry_after_seconds = (
            min(retry_after_seconds, 86_400)
            if isinstance(retry_after_seconds, int)
            and not isinstance(retry_after_seconds, bool)
            and retry_after_seconds >= 0
            else None
        )
        super().__init__(self.category)

    @property
    def safe_metadata(self) -> MappingProxyType[str, str | int | None]:
        return MappingProxyType(
            {
                "category": self.category,
                "call_session_id": (
                    str(self.call_session_id) if self.call_session_id is not None else None
                ),
                "destination_label": self.destination_label,
                "provider_request_id": self.provider_request_id,
                "retry_after_seconds": self.retry_after_seconds,
            }
        )


class OutboundCallAuthorizationError(OutboundCallError):
    category = "authorization"


class OutboundCallAllowlistError(OutboundCallError):
    category = "allowlist"


class OutboundCallIdempotencyConflict(OutboundCallError):
    category = "idempotency_conflict"


class OutboundCallAuthenticationError(OutboundCallError):
    category = "authentication"


class OutboundCallRateLimitError(OutboundCallError):
    category = "rate_limit"


class OutboundCallTimeoutError(OutboundCallError):
    category = "timeout"


class OutboundCallOutcomeUncertain(OutboundCallError):
    category = "uncertain_outcome"


class InvalidOutboundCallResponseError(OutboundCallError):
    category = "invalid_response"


class OutboundCallProviderError(OutboundCallError):
    category = "provider"
