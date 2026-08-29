import json
from collections.abc import Mapping
from typing import Any

import pytest
from app.config import Settings
from app.contract_service import (
    ContractResult,
    ContractServiceError,
    JsonValue,
    get_contract_service,
)
from app.main import create_app
from app.schemas.errors import ApiErrorCode
from contract_fixtures import IDS, request_for, response_for
from fastapi.testclient import TestClient

AUTH = {"Authorization": "Bearer synthetic-test-token"}
MUTATION_HEADERS = {**AUTH, "Idempotency-Key": "synthetic-key-001"}

ROUTES = {
    "create_operation_draft": ("POST", "/v1/operation-drafts", 201),
    "approve_operation": ("POST", "/v1/operations", 201),
    "get_operation": ("GET", f"/v1/operations/{IDS['operation']}", 200),
    "start_negotiation": (
        "POST",
        f"/v1/operations/{IDS['operation']}/negotiations",
        201,
    ),
    "record_quote": ("POST", f"/v1/calls/{IDS['call']}/quotes", 201),
    "attach_commitment_evidence": ("POST", f"/v1/calls/{IDS['call']}/evidence", 201),
    "create_candidate_commitment": (
        "POST",
        f"/v1/calls/{IDS['call']}/commitments",
        201,
    ),
    "create_simulated_recap": ("POST", f"/v1/calls/{IDS['call']}/recaps", 201),
    "create_call_brief": ("POST", f"/v1/calls/{IDS['call']}/briefs", 201),
    "start_inbound_simulation": (
        "POST",
        f"/v1/operations/{IDS['operation']}/inbound-simulations",
        201,
    ),
    "replace_mandate": ("POST", f"/v1/operations/{IDS['operation']}/mandates", 201),
    "create_escalation": ("POST", f"/v1/calls/{IDS['call']}/escalations", 201),
    "acknowledge_notification": (
        "POST",
        f"/v1/notifications/{IDS['notification']}/acknowledgements",
        200,
    ),
    "get_operation_audit": ("GET", f"/v1/operations/{IDS['operation']}/audit", 200),
}


class DeterministicFake:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, JsonValue], str | None]] = []
        self.idempotency: dict[str, tuple[str, ContractResult]] = {}
        self.error: Exception | None = None

    async def execute(
        self,
        operation_id: str,
        payload: dict[str, JsonValue],
        idempotency_key: str | None,
    ) -> ContractResult:
        self.calls.append((operation_id, payload, idempotency_key))
        if self.error is not None:
            raise self.error

        result = ContractResult(response_for(operation_id))
        if idempotency_key is None:
            return result

        normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        existing = self.idempotency.get(idempotency_key)
        if existing is None:
            self.idempotency[idempotency_key] = (normalized, result)
            return result
        previous_request, previous_result = existing
        if previous_request != normalized:
            raise ContractServiceError(
                status_code=409,
                code=ApiErrorCode.IDEMPOTENCY_KEY_REUSED,
                message="The idempotency key belongs to a different request.",
            )
        return ContractResult(previous_result.payload, idempotency_replayed=True)


def build_client(fake: DeterministicFake | None = None) -> TestClient:
    app = create_app(
        Settings(
            app_env="test",
            volta_demo_bearer_token="synthetic-test-token",
            cors_origins=["http://localhost:3000"],
        )
    )
    if fake is not None:
        app.dependency_overrides[get_contract_service] = lambda: fake
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize(("operation_id", "route"), ROUTES.items())
def test_every_route_serializes_its_typed_success_contract(
    operation_id: str,
    route: tuple[str, str, int],
) -> None:
    fake = DeterministicFake()
    method, path, expected_status = route
    body = request_for(operation_id)
    headers = MUTATION_HEADERS if method == "POST" else AUTH

    with build_client(fake) as client:
        response = client.request(method, path, headers=headers, json=body)

    assert response.status_code == expected_status, response.text
    assert response.json() == response_for(operation_id)
    assert response.headers["x-request-id"]
    assert fake.calls[0][0] == operation_id


def test_default_service_returns_honest_not_implemented_after_validation() -> None:
    with build_client() as client:
        response = client.post(
            "/v1/operation-drafts",
            headers=MUTATION_HEADERS,
            json=request_for("create_operation_draft"),
        )

    assert response.status_code == 501
    assert response.json() == {
        "code": "CONTRACT_NOT_IMPLEMENTED",
        "message": "This contract is not connected to an application service yet.",
        "request_id": response.headers["x-request-id"],
        "field_issues": None,
        "resource_id": None,
        "current_operation_version": None,
    }


def test_authentication_is_rejected_before_contract_delegation() -> None:
    fake = DeterministicFake()
    with build_client(fake) as client:
        missing = client.post("/v1/operation-drafts", json={"unknown": "submitted-secret"})
        invalid = client.post(
            "/v1/operation-drafts",
            headers={"Authorization": "Bearer submitted-secret"},
            json={"unknown": "submitted-secret"},
        )

    assert missing.status_code == 401
    assert missing.json()["code"] == "AUTHENTICATION_REQUIRED"
    assert invalid.status_code == 401
    assert invalid.json()["code"] == "AUTHENTICATION_INVALID"
    assert "submitted-secret" not in missing.text + invalid.text
    assert fake.calls == []


def test_validation_error_is_safe_and_preserves_request_id() -> None:
    fake = DeterministicFake()
    with build_client(fake) as client:
        response = client.post(
            "/v1/operation-drafts",
            headers={**MUTATION_HEADERS, "X-Request-ID": "contract-validation-1"},
            json={
                **request_for("create_operation_draft"),
                "source_prompt": "submitted-secret-prompt",
                "server_owned_state": "ACTIVE",
            },
        )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["request_id"] == "contract-validation-1"
    assert body["field_issues"][0]["field"] == "body.server_owned_state"
    assert "submitted-secret-prompt" not in response.text
    assert fake.calls == []


def test_idempotency_replay_and_changed_request_conflict_are_fake_driven() -> None:
    fake = DeterministicFake()
    original = request_for("create_operation_draft")
    assert original is not None
    with build_client(fake) as client:
        first = client.post("/v1/operation-drafts", headers=MUTATION_HEADERS, json=original)
        replay = client.post("/v1/operation-drafts", headers=MUTATION_HEADERS, json=original)
        conflict = client.post(
            "/v1/operation-drafts",
            headers=MUTATION_HEADERS,
            json={**original, "requested_language": "ES_MX"},
        )

    assert first.status_code == 201
    assert "idempotency-replayed" not in first.headers
    assert replay.status_code == 201
    assert replay.headers["idempotency-replayed"] == "true"
    assert replay.json() == first.json()
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "IDEMPOTENCY_KEY_REUSED"


@pytest.mark.parametrize(
    ("operation_id", "code", "current_version"),
    [
        ("approve_operation", ApiErrorCode.STALE_DRAFT_VERSION, None),
        ("start_negotiation", ApiErrorCode.STALE_OPERATION_VERSION, 4),
    ],
)
def test_stale_version_errors_map_without_internal_state(
    operation_id: str,
    code: ApiErrorCode,
    current_version: int | None,
) -> None:
    fake = DeterministicFake()
    fake.error = ContractServiceError(
        status_code=409,
        code=code,
        message="The submitted version is stale.",
        current_operation_version=current_version,
    )
    method, path, _ = ROUTES[operation_id]

    with build_client(fake) as client:
        response = client.request(
            method,
            path,
            headers=MUTATION_HEADERS,
            json=request_for(operation_id),
        )

    assert response.status_code == 409
    assert response.json()["code"] == code
    assert response.json()["current_operation_version"] == current_version
    assert "ContractServiceError" not in response.text


@pytest.mark.parametrize(
    ("status_code", "code"),
    [
        (403, ApiErrorCode.ACTION_NOT_AUTHORIZED),
        (404, ApiErrorCode.RESOURCE_NOT_FOUND),
        (409, ApiErrorCode.STATE_CONFLICT),
        (409, ApiErrorCode.MANDATE_CONFLICT),
        (429, ApiErrorCode.RATE_LIMITED),
    ],
)
def test_application_failures_use_the_safe_error_envelope(
    status_code: int,
    code: ApiErrorCode,
) -> None:
    fake = DeterministicFake()
    fake.error = ContractServiceError(
        status_code=status_code,
        code=code,
        message="The requested action cannot proceed.",
        resource_id=IDS["operation"] if status_code == 404 else None,
    )
    with build_client(fake) as client:
        response = client.get(f"/v1/operations/{IDS['operation']}", headers=AUTH)

    assert response.status_code == status_code
    assert response.json()["code"] == code
    assert response.json()["request_id"] == response.headers["x-request-id"]


def test_unexpected_error_is_translated_without_exception_details() -> None:
    fake = DeterministicFake()
    fake.error = RuntimeError("submitted-secret and internal stack detail")
    with build_client(fake) as client:
        response = client.get(f"/v1/operations/{IDS['operation']}", headers=AUTH)

    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_ERROR"
    assert "submitted-secret" not in response.text
    assert "RuntimeError" not in response.text


def test_cors_is_credentialed_and_limited_to_explicit_origins_and_headers() -> None:
    with build_client() as client:
        actual = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"},
        )
        allowed = client.options(
            "/v1/operation-drafts",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": (
                    "authorization,idempotency-key,content-type,x-request-id"
                ),
            },
        )
        rejected = client.options(
            "/v1/operation-drafts",
            headers={
                "Origin": "https://untrusted.example",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert actual.status_code == 200
    assert actual.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert actual.headers["access-control-allow-credentials"] == "true"
    exposed_headers = actual.headers["access-control-expose-headers"].lower()
    assert "x-request-id" in exposed_headers
    assert "idempotency-replayed" in exposed_headers
    assert actual.headers["x-request-id"]
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert allowed.headers["access-control-allow-credentials"] == "true"
    assert allowed.headers["x-request-id"]
    allowed_headers = allowed.headers["access-control-allow-headers"].lower()
    for header in ("authorization", "idempotency-key", "content-type", "x-request-id"):
        assert header in allowed_headers
    assert rejected.status_code == 400
    assert "access-control-allow-origin" not in rejected.headers
    assert rejected.headers["x-request-id"]


def _request_schema(schema: Mapping[str, Any], operation: Mapping[str, Any]) -> Mapping[str, Any]:
    reference = operation["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    return schema["components"]["schemas"][reference.rsplit("/", maxsplit=1)[-1]]


def test_openapi_has_stable_secure_generated_client_contract() -> None:
    schema = build_client().app.openapi()
    operations: dict[str, Mapping[str, Any]] = {}
    for path, path_item in schema["paths"].items():
        if path == "/health":
            assert "security" not in path_item["get"]
            continue
        assert path.startswith("/v1/")
        for method, operation in path_item.items():
            if method not in {"get", "post"}:
                continue
            operations[operation["operationId"]] = operation
            assert operation["security"] == [{"HTTPBearer": []}]
            assert "401" in operation["responses"]
            assert "501" in operation["responses"]
            if method == "post":
                parameters = {item["name"]: item for item in operation["parameters"]}
                assert parameters["Idempotency-Key"]["required"] is True
                assert _request_schema(schema, operation)["additionalProperties"] is False

    assert set(operations) == set(ROUTES)
    assert len(operations) == 14
    assert len(set(operations)) == 14
    assert "example" not in json.dumps(schema["components"]["securitySchemes"]["HTTPBearer"])

    approve_schema = _request_schema(schema, operations["approve_operation"])
    assert "expected_draft_version" in approve_schema["required"]
    assert "404" not in operations["create_operation_draft"]["responses"]
    assert "404" in operations["approve_operation"]["responses"]
    for operation_id, operation in operations.items():
        versionless_operations = {
            "create_operation_draft",
            "approve_operation",
            "get_operation",
            "get_operation_audit",
        }
        if operation_id in versionless_operations:
            continue
        assert "expected_operation_version" in _request_schema(schema, operation)["required"]
