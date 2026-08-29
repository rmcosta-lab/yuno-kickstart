"""Safe application errors for negotiation mutations."""

from uuid import UUID

__all__ = [
    "CallSessionNotFound",
    "CarrierSessionMismatch",
    "IdempotencyConflict",
    "InvalidNegotiationTransition",
    "NegotiationAlreadyStarted",
    "OperationNotFound",
    "QuoteExpired",
    "QuoteNotBestCandidate",
    "QuoteNotEligible",
    "QuoteNotFound",
    "StaleMandateVersion",
    "StaleOperationVersion",
]


class _SafeNegotiationError(RuntimeError):
    code = "negotiation_error"


class OperationNotFound(_SafeNegotiationError, LookupError):
    code = "operation_not_found"

    def __init__(self, operation_id: UUID) -> None:
        self.operation_id = operation_id
        super().__init__(f"operation not found: {operation_id}")


class StaleOperationVersion(_SafeNegotiationError):
    code = "stale_operation_version"

    def __init__(self, operation_id: UUID, expected_version: int, current_version: int) -> None:
        self.operation_id = operation_id
        self.expected_version = expected_version
        self.current_version = current_version
        super().__init__(
            f"stale operation version: {operation_id} "
            f"(expected={expected_version}, current={current_version})"
        )


class StaleMandateVersion(_SafeNegotiationError):
    code = "stale_mandate_version"

    def __init__(self, operation_id: UUID, expected_version: int, current_version: int) -> None:
        self.operation_id = operation_id
        self.expected_version = expected_version
        self.current_version = current_version
        super().__init__(
            f"stale mandate version: {operation_id} "
            f"(expected={expected_version}, current={current_version})"
        )


class NegotiationAlreadyStarted(_SafeNegotiationError):
    code = "negotiation_already_started"

    def __init__(self, operation_id: UUID, negotiation_id: UUID) -> None:
        self.operation_id = operation_id
        self.negotiation_id = negotiation_id
        super().__init__(f"negotiation already started: {operation_id}")


class CallSessionNotFound(_SafeNegotiationError, LookupError):
    code = "call_session_not_found"

    def __init__(self, call_id: UUID) -> None:
        self.call_id = call_id
        super().__init__(f"call session not found: {call_id}")


class CarrierSessionMismatch(_SafeNegotiationError):
    code = "carrier_session_mismatch"

    def __init__(self, call_id: UUID, carrier_id: UUID) -> None:
        self.call_id = call_id
        self.carrier_id = carrier_id
        super().__init__(f"carrier session mismatch: {call_id} carrier={carrier_id}")


class QuoteNotFound(_SafeNegotiationError, LookupError):
    code = "quote_not_found"

    def __init__(self, quote_id: UUID) -> None:
        self.quote_id = quote_id
        super().__init__(f"quote not found: {quote_id}")


class QuoteNotEligible(_SafeNegotiationError):
    code = "quote_not_eligible"

    def __init__(self, quote_id: UUID, reason_codes: tuple[str, ...] = ()) -> None:
        self.quote_id = quote_id
        self.reason_codes = reason_codes
        super().__init__(f"quote not eligible: {quote_id}")


class QuoteExpired(_SafeNegotiationError):
    code = "quote_expired"

    def __init__(self, quote_id: UUID) -> None:
        self.quote_id = quote_id
        super().__init__(f"quote expired: {quote_id}")


class QuoteNotBestCandidate(_SafeNegotiationError):
    code = "quote_not_best_candidate"

    def __init__(self, quote_id: UUID, best_quote_id: UUID) -> None:
        self.quote_id = quote_id
        self.best_quote_id = best_quote_id
        super().__init__(f"quote not best candidate: {quote_id} best={best_quote_id}")


class InvalidNegotiationTransition(_SafeNegotiationError):
    code = "invalid_negotiation_transition"

    def __init__(self, operation_id: UUID, reason_code: str) -> None:
        self.operation_id = operation_id
        self.reason_code = reason_code
        super().__init__(f"invalid negotiation transition: {operation_id} ({reason_code})")


class IdempotencyConflict(_SafeNegotiationError):
    code = "idempotency_conflict"

    def __init__(self, operation_id: UUID, operation_name: str, key: str) -> None:
        self.operation_id = operation_id
        self.operation_name = operation_name
        super().__init__(f"idempotency conflict: {operation_id} operation={operation_name}")
