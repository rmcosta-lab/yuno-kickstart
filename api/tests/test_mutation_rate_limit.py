from concurrent.futures import ThreadPoolExecutor

from app.config import Settings
from app.contract_service import ContractResult, JsonValue, get_contract_service
from app.main import create_app
from app.middleware.rate_limit import SlidingWindowRateLimiter
from contract_fixtures import IDS, request_for, response_for
from fastapi.testclient import TestClient

AUTH = {"Authorization": "Bearer synthetic-test-token"}


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class RecordingService:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def execute(
        self,
        operation_id: str,
        payload: dict[str, JsonValue],
        idempotency_key: str | None,
    ) -> ContractResult:
        del payload, idempotency_key
        self.calls.append(operation_id)
        return ContractResult(response_for(operation_id))


def build_client(
    service: RecordingService,
    clock: FakeClock,
    *,
    request_limit: int = 2,
    window_seconds: float = 10.0,
) -> TestClient:
    application = create_app(
        Settings(
            app_env="test",
            volta_demo_bearer_token="synthetic-test-token",
            cors_origins=["http://localhost:3000"],
            volta_mutation_rate_limit_requests=request_limit,
            volta_mutation_rate_limit_window_seconds=window_seconds,
            volta_mutation_rate_limit_max_identities=8,
        ),
        mutation_rate_limit_clock=clock,
    )
    application.dependency_overrides[get_contract_service] = lambda: service
    return TestClient(application, raise_server_exceptions=False)


def mutation_headers(key: str, **extra: str) -> dict[str, str]:
    return {**AUTH, "Idempotency-Key": key, **extra}


def test_mutation_boundary_returns_stable_429_without_delegating() -> None:
    service = RecordingService()
    clock = FakeClock()
    body = request_for("create_operation_draft")
    with build_client(service, clock) as client:
        first = client.post(
            "/v1/operation-drafts",
            headers=mutation_headers("rate-key-001"),
            json=body,
        )
        second = client.post(
            "/v1/operation-drafts",
            headers=mutation_headers("rate-key-002"),
            json=body,
        )
        limited = client.post(
            "/v1/operation-drafts",
            headers=mutation_headers(
                "rate-key-003",
                **{
                    "Origin": "http://localhost:3000",
                    "X-Request-ID": "rate-boundary-1",
                },
            ),
            json=body,
        )

    assert first.status_code == second.status_code == 201
    assert limited.status_code == 429
    assert limited.json() == {
        "code": "RATE_LIMITED",
        "message": "The configured demo traffic boundary was exceeded.",
        "request_id": "rate-boundary-1",
        "field_issues": None,
        "resource_id": None,
        "current_draft_version": None,
        "current_operation_version": None,
    }
    assert limited.headers["x-request-id"] == "rate-boundary-1"
    assert limited.headers["retry-after"] == "10"
    assert limited.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert service.calls == ["create_operation_draft", "create_operation_draft"]


def test_window_reopens_deterministically_at_its_boundary() -> None:
    service = RecordingService()
    clock = FakeClock()
    body = request_for("create_operation_draft")
    with build_client(service, clock, request_limit=1) as client:
        accepted = client.post(
            "/v1/operation-drafts",
            headers=mutation_headers("window-key-001"),
            json=body,
        )
        blocked = client.post(
            "/v1/operation-drafts",
            headers=mutation_headers("window-key-002"),
            json=body,
        )
        clock.advance(10.0)
        reopened = client.post(
            "/v1/operation-drafts",
            headers=mutation_headers("window-key-003"),
            json=body,
        )

    assert accepted.status_code == reopened.status_code == 201
    assert blocked.status_code == 429
    assert service.calls == ["create_operation_draft", "create_operation_draft"]


def test_untrusted_origin_cannot_create_a_new_rate_limit_identity() -> None:
    service = RecordingService()
    clock = FakeClock()
    body = request_for("create_operation_draft")
    with build_client(service, clock, request_limit=1) as client:
        accepted = client.post(
            "/v1/operation-drafts",
            headers=mutation_headers("origin-key-001", Origin="http://localhost:3000"),
            json=body,
        )
        blocked = client.post(
            "/v1/operation-drafts",
            headers=mutation_headers("origin-key-002", Origin="https://untrusted.example"),
            json=body,
        )

    assert accepted.status_code == 201
    assert blocked.status_code == 429
    assert service.calls == ["create_operation_draft"]


def test_invalid_auth_reads_health_and_preflight_do_not_consume_mutation_capacity() -> None:
    service = RecordingService()
    clock = FakeClock()
    with build_client(service, clock, request_limit=1) as client:
        invalid = client.post(
            "/v1/operation-drafts",
            headers={
                "Authorization": "Bearer wrong-token",
                "Idempotency-Key": "invalid-auth-key",
            },
            json=request_for("create_operation_draft"),
        )
        for _ in range(3):
            assert client.get("/health").status_code == 200
            assert (
                client.get(f"/v1/operations/{IDS['operation']}", headers=AUTH).status_code
                == 200
            )
            assert (
                client.options(
                    "/v1/operation-drafts",
                    headers={
                        "Origin": "http://localhost:3000",
                        "Access-Control-Request-Method": "POST",
                    },
                ).status_code
                == 200
            )
        mutation = client.post(
            "/v1/operation-drafts",
            headers=mutation_headers("remaining-key-001"),
            json=request_for("create_operation_draft"),
        )

    assert invalid.status_code == 401
    assert mutation.status_code == 201
    assert service.calls.count("create_operation_draft") == 1


def test_limiter_is_concurrency_safe_and_identity_storage_is_bounded() -> None:
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(
        request_limit=1,
        window_seconds=10.0,
        max_identities=2,
        clock=clock,
    )

    with ThreadPoolExecutor(max_workers=8) as executor:
        decisions = list(executor.map(lambda _: limiter.check(b"same-identity"), range(8)))

    assert sum(decision.allowed for decision in decisions) == 1
    assert all(decision.retry_after_seconds == 10 for decision in decisions if not decision.allowed)
    assert limiter.check(b"second-identity").allowed is True
    assert limiter.check(b"third-identity").allowed is True
    assert limiter.identity_count == 2
