from __future__ import annotations

import ast
from datetime import datetime
from pathlib import Path

import yuno_backend.volta.telephony as telephony
from yuno_backend.volta.telephony import (
    OutboundCall,
    OutboundCallAttempt,
    OutboundCallAttemptReservation,
    OutboundCallAttemptState,
    OutboundCallAttemptStore,
    OutboundCallFailure,
    OutboundCallGateway,
    OutboundCallRequest,
    OutboundCallUncertainState,
)


def test_public_surface_matches_frozen_phase_contract() -> None:
    assert set(telephony.__all__) == {
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
    }


def test_provider_neutral_package_has_no_framework_provider_or_transport_imports() -> None:
    package_root = Path(__file__).parents[3] / "src" / "yuno_backend" / "volta" / "telephony"
    forbidden_roots = {
        "fastapi",
        "frontend",
        "httpx",
        "openai",
        "pydantic",
        "sqlalchemy",
        "twilio",
    }
    imported: list[str] = []
    for source_file in package_root.rglob("*.py"):
        tree = ast.parse(source_file.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)

    violations = [name for name in imported if name.split(".")[0] in forbidden_roots]
    violations.extend(
        name
        for name in imported
        if name.startswith("yuno_backend.integrations")
        or name.startswith("yuno_backend.volta.persistence")
        or name.startswith("yuno_backend.payments")
    )
    assert not violations


def test_gateway_and_atomic_store_are_runtime_protocols() -> None:
    class Gateway:
        async def create_call(self, request: OutboundCallRequest) -> OutboundCall:
            raise NotImplementedError

    class Store:
        async def reserve(
            self, attempt: OutboundCallAttempt
        ) -> OutboundCallAttemptReservation:
            raise NotImplementedError

        async def complete(
            self,
            idempotency_key: str,
            request_fingerprint: str,
            result: OutboundCall,
            completed_at: datetime,
        ) -> OutboundCallAttempt:
            raise NotImplementedError

        async def mark_uncertain(
            self,
            idempotency_key: str,
            request_fingerprint: str,
            uncertainty: OutboundCallUncertainState,
        ) -> OutboundCallAttempt:
            raise NotImplementedError

        async def fail(
            self,
            idempotency_key: str,
            request_fingerprint: str,
            failure: OutboundCallFailure,
        ) -> OutboundCallAttempt:
            raise NotImplementedError

    assert isinstance(Gateway(), OutboundCallGateway)
    assert isinstance(Store(), OutboundCallAttemptStore)


def test_reservation_elects_only_a_new_pending_attempt(
    call_request: OutboundCallRequest, fixed_now: datetime
) -> None:
    attempt = OutboundCallAttempt(
        operation_id=call_request.operation_id,
        idempotency_key=call_request.idempotency_key,
        request_fingerprint="a" * 64,
        state=OutboundCallAttemptState.PENDING,
        result=None,
        uncertainty=None,
        failure=None,
        created_at=fixed_now,
        updated_at=fixed_now,
    )
    reservation = OutboundCallAttemptReservation(attempt=attempt, created=True)
    assert reservation.created is True
    assert reservation.attempt is attempt
