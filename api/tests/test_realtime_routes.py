from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import httpx
import pytest
from app.config import Settings
from app.contract_service import ContractServiceError
from app.main import create_app
from app.middleware.rate_limit import SlidingWindowRateLimiter
from app.openai_client import get_openai_http_client
from app.realtime_service import (
    RealtimeClientSecretService,
    build_realtime_client_secret_service,
    derive_safety_identifier,
    get_realtime_client_secret_service,
)
from app.schemas.errors import ApiErrorCode
from fastapi.testclient import TestClient
from yuno_backend.volta.realtime import (
    RealtimeClientSecret,
    RealtimeClientSecretRequest,
    RealtimeProviderError,
)

AUTH = {"Authorization": "Bearer synthetic-test-token"}
ORIGIN = {"Origin": "http://localhost:3000"}
NO_STORE = "no-store, private, max-age=0"


@dataclass
class FakeHttpService:
    calls: int = 0
    error: Exception | None = None

    async def issue(self):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return {
            "client_secret": "ephemeral-sensitive-marker",
            "expires_at": 1_788_000_060,
            "session_id": "sess.synthetic",
            "model": "gpt-realtime-2.1",
        }


def build_client(
    service: object,
    *,
    request_limit: int = 30,
) -> TestClient:
    application = create_app(
        Settings(
            app_env="test",
            cors_origins=["http://localhost:3000"],
            volta_demo_bearer_token="synthetic-test-token",
            volta_mutation_rate_limit_requests=request_limit,
            volta_mutation_rate_limit_window_seconds=60,
            openai_api_key="standard-sensitive-marker",
            openai_realtime_safety_identifier_key="derivation-sensitive-marker",
        )
    )
    application.dependency_overrides[get_realtime_client_secret_service] = lambda: service
    return TestClient(application, raise_server_exceptions=False)


def assert_no_store(response) -> None:
    assert response.headers["cache-control"] == NO_STORE
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["x-request-id"]


def test_authorized_origin_receives_only_typed_credential_fields() -> None:
    service = FakeHttpService()
    with build_client(service) as client:
        response = client.post(
            "/v1/realtime/client-secrets",
            headers={**AUTH, **ORIGIN, "X-Request-ID": "realtime-success-1"},
        )

    assert response.status_code == 201
    assert response.json() == {
        "client_secret": "ephemeral-sensitive-marker",
        "expires_at": 1_788_000_060,
        "session_id": "sess.synthetic",
        "model": "gpt-realtime-2.1",
    }
    assert response.headers["x-request-id"] == "realtime-success-1"
    assert_no_store(response)
    assert service.calls == 1


@pytest.mark.parametrize(
    ("headers", "status_code", "code"),
    [
        ({**ORIGIN}, 401, "AUTHENTICATION_REQUIRED"),
        (
            {**ORIGIN, "Authorization": "Bearer invalid-sensitive-marker"},
            401,
            "AUTHENTICATION_INVALID",
        ),
        ({**AUTH}, 403, "ACTION_NOT_AUTHORIZED"),
        ({**AUTH, "Origin": "https://untrusted.example"}, 403, "ACTION_NOT_AUTHORIZED"),
    ],
)
def test_authentication_and_exact_origin_reject_before_issuance(
    headers: dict[str, str], status_code: int, code: str
) -> None:
    service = FakeHttpService()
    with build_client(service) as client:
        response = client.post("/v1/realtime/client-secrets", headers=headers)

    assert response.status_code == status_code
    assert response.json()["code"] == code
    assert "sensitive-marker" not in response.text
    assert_no_store(response)
    if status_code == 401:
        assert response.headers["www-authenticate"] == "Bearer"
    assert service.calls == 0


def test_rate_limit_has_retry_and_no_store_without_extra_issuance() -> None:
    service = FakeHttpService()
    with build_client(service, request_limit=1) as client:
        accepted = client.post("/v1/realtime/client-secrets", headers={**AUTH, **ORIGIN})
        limited = client.post("/v1/realtime/client-secrets", headers={**AUTH, **ORIGIN})

    assert accepted.status_code == 201
    assert limited.status_code == 429
    assert limited.json()["code"] == "RATE_LIMITED"
    assert limited.headers["retry-after"] == "60"
    assert_no_store(limited)
    assert service.calls == 1


def test_invalid_realtime_origin_never_consumes_authorized_rate_limit() -> None:
    service = FakeHttpService()
    invalid_origin = {**AUTH, "Origin": "https://untrusted.example"}
    with build_client(service, request_limit=1) as client:
        first_rejected = client.post("/v1/realtime/client-secrets", headers=invalid_origin)
        second_rejected = client.post("/v1/realtime/client-secrets", headers=invalid_origin)
        accepted = client.post("/v1/realtime/client-secrets", headers={**AUTH, **ORIGIN})
        limited = client.post("/v1/realtime/client-secrets", headers={**AUTH, **ORIGIN})

    assert first_rejected.status_code == 403
    assert second_rejected.status_code == 403
    assert accepted.status_code == 201
    assert limited.status_code == 429
    assert service.calls == 1


def test_safe_service_error_and_unexpected_error_are_not_cached() -> None:
    safe = FakeHttpService(
        error=ContractServiceError(
            status_code=502,
            code=ApiErrorCode.REALTIME_UNAVAILABLE,
            message="Realtime credential issuance is temporarily unavailable.",
        )
    )
    unexpected = FakeHttpService(error=RuntimeError("provider-sensitive-marker"))
    with build_client(safe) as client:
        unavailable = client.post("/v1/realtime/client-secrets", headers={**AUTH, **ORIGIN})
    with build_client(unexpected) as client:
        internal = client.post("/v1/realtime/client-secrets", headers={**AUTH, **ORIGIN})

    assert unavailable.status_code == 502
    assert unavailable.json()["code"] == "REALTIME_UNAVAILABLE"
    assert internal.status_code == 500
    assert internal.json()["code"] == "INTERNAL_ERROR"
    assert "provider-sensitive-marker" not in internal.text
    assert_no_store(unavailable)
    assert_no_store(internal)


class RecordingIssuer:
    def __init__(self) -> None:
        self.requests: list[RealtimeClientSecretRequest] = []
        self.error: Exception | None = None

    async def issue(self, request: RealtimeClientSecretRequest) -> RealtimeClientSecret:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return RealtimeClientSecret(
            value="ephemeral-sensitive-marker",
            expires_at=1_788_000_060,
            session_id="sess.synthetic",
            model_id="gpt-realtime-2.1",
        )


@pytest.mark.asyncio
async def test_service_derives_stable_private_identifier_and_narrow_session() -> None:
    issuer = RecordingIssuer()
    service = RealtimeClientSecretService(
        issuer,
        safety_identifier_key="derivation-sensitive-marker",
        subject="demo-coordinator",
        voice="marin",
    )

    result = await service.issue()

    session = issuer.requests[0].session
    expected = derive_safety_identifier("derivation-sensitive-marker", "demo-coordinator")
    assert session.safety_identifier == expected
    assert len(expected) == 64 and expected == expected.lower()
    assert session.language == "en"
    assert session.voice == "marin"
    assert session.vad == "server_vad"
    assert {tool.name for tool in session.tools} == {
        "record_quote",
        "create_candidate_commitment",
    }
    tools = {tool.name: tool.parameters for tool in session.tools}
    assert tools["record_quote"]["required"] == (
        "call_id",
        "expected_operation_version",
        "carrier_id",
        "mandate_version",
        "terms",
        "valid_until",
    )
    assert tools["record_quote"]["properties"]["terms"]["required"] == (
        "amount_minor",
        "currency",
        "pickup_window",
        "conditions",
    )
    assert tools["record_quote"]["properties"]["terms"]["properties"]["currency"] == {
        "type": "string",
        "enum": ("MXN",),
    }
    assert tools["create_candidate_commitment"]["required"] == (
        "call_id",
        "expected_operation_version",
        "quote_id",
        "mandate_version",
        "evidence_id",
    )
    assert all(
        schema["additionalProperties"] is False
        for schema in (
            tools["record_quote"],
            tools["record_quote"]["properties"]["terms"],
            tools["record_quote"]["properties"]["terms"]["properties"]["pickup_window"],
            tools["create_candidate_commitment"],
        )
    )
    assert result.client_secret == "ephemeral-sensitive-marker"
    assert "ephemeral-sensitive-marker" not in repr(result)
    assert "derivation-sensitive-marker" not in repr(issuer.requests[0])


@pytest.mark.asyncio
async def test_service_maps_all_provider_neutral_realtime_failures_safely() -> None:
    issuer = RecordingIssuer()
    issuer.error = RealtimeProviderError(
        request_id="provider-request-id",
        status_code=500,
    )
    service = RealtimeClientSecretService(
        issuer,
        safety_identifier_key="derivation-sensitive-marker",
        subject="demo-coordinator",
        voice="marin",
    )

    with pytest.raises(ContractServiceError) as captured:
        await service.issue()

    assert captured.value.status_code == 502
    assert captured.value.code is ApiErrorCode.REALTIME_UNAVAILABLE
    assert "provider-request-id" not in captured.value.safe_message


def test_safety_identifier_changes_with_key_and_subject() -> None:
    baseline = derive_safety_identifier("key-a", "subject-a")
    assert baseline == derive_safety_identifier("key-a", "subject-a")
    assert baseline != derive_safety_identifier("key-b", "subject-a")
    assert baseline != derive_safety_identifier("key-a", "subject-b")


def test_concurrent_requests_cannot_bypass_one_identity_limit() -> None:
    limiter = SlidingWindowRateLimiter(
        request_limit=1,
        window_seconds=60,
        max_identities=8,
        clock=lambda: 100.0,
    )
    with ThreadPoolExecutor(max_workers=8) as executor:
        decisions = list(executor.map(lambda _: limiter.check(b"demo-identity"), range(8)))
    assert sum(decision.allowed for decision in decisions) == 1


def test_openapi_freezes_no_body_security_and_error_contracts() -> None:
    service = FakeHttpService()
    with build_client(service) as client:
        operation = client.get("/openapi.json").json()["paths"]["/v1/realtime/client-secrets"][
            "post"
        ]

    assert operation["operationId"] == "create_realtime_client_secret"
    assert "requestBody" not in operation
    assert operation["security"] == [{"HTTPBearer": []}]
    assert set(operation["responses"]) == {"201", "401", "403", "429", "500", "502"}
    assert operation["responses"]["201"]["headers"]["Cache-Control"]
    assert operation["responses"]["401"]["headers"]["WWW-Authenticate"]["schema"] == {
        "type": "string",
        "enum": ["Bearer"],
    }


def test_concurrent_first_use_retains_and_lifespan_closes_exactly_one_client() -> None:
    application = create_app(Settings(app_env="test"))
    created: list[httpx.AsyncClient] = []

    def factory() -> httpx.AsyncClient:
        client = httpx.AsyncClient()
        created.append(client)
        return client

    application.state.openai_http_client_factory = factory
    with ThreadPoolExecutor(max_workers=8) as executor:
        clients = list(executor.map(lambda _: get_openai_http_client(application), range(32)))

    assert len(created) == 1
    assert all(client is created[0] for client in clients)
    assert application.state.openai_http_client is created[0]
    assert created[0].is_closed is False

    with TestClient(application):
        assert application.state.openai_http_client is created[0]

    assert created[0].is_closed is True


@pytest.mark.asyncio
async def test_realtime_service_leaves_official_url_ownership_to_backend_config() -> None:
    settings = Settings(
        app_env="test",
        openai_api_key="standard-sensitive-marker",
        openai_base_url="https://extraction-only.example/v1",
        openai_realtime_safety_identifier_key="derivation-sensitive-marker",
    )
    async with httpx.AsyncClient() as client:
        service = build_realtime_client_secret_service(settings, client)

    assert service._issuer._config.url == "https://api.openai.com/v1/realtime/client_secrets"
