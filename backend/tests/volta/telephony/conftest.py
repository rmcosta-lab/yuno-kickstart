from datetime import UTC, datetime
from uuid import UUID

import pytest
from yuno_backend.volta.telephony import (
    OutboundCall,
    OutboundCallAuthorization,
    OutboundCallRequest,
    OutboundCallStatus,
)


@pytest.fixture
def fixed_now() -> datetime:
    return datetime(2026, 8, 30, 12, 0, tzinfo=UTC)


@pytest.fixture
def authorization(fixed_now: datetime) -> OutboundCallAuthorization:
    return OutboundCallAuthorization(actor_id="operator.demo", authorized_at=fixed_now)


@pytest.fixture
def call_request(authorization: OutboundCallAuthorization) -> OutboundCallRequest:
    return OutboundCallRequest(
        operation_id=UUID("10000000-0000-0000-0000-000000000001"),
        call_session_id=UUID("20000000-0000-0000-0000-000000000002"),
        correlation_id=UUID("30000000-0000-0000-0000-000000000003"),
        idempotency_key="call-attempt-demo-001",
        destination_label="carrier.demo.primary",
        authorization=authorization,
    )


@pytest.fixture
def outbound_call(call_request: OutboundCallRequest, fixed_now: datetime) -> OutboundCall:
    return OutboundCall(
        call_session_id=call_request.call_session_id,
        provider_call_id="provider.call.safe",
        status=OutboundCallStatus.QUEUED,
        created_at=fixed_now,
    )
