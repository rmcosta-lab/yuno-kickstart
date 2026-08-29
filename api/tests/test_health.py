from app.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


def build_client() -> TestClient:
    return TestClient(create_app(Settings(app_env="test")))


def test_health_returns_typed_contract_and_correlation_id() -> None:
    with build_client() as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-request-id"]


def test_health_preserves_a_safe_incoming_correlation_id() -> None:
    with build_client() as client:
        response = client.get("/health", headers={"x-request-id": "demo-request_1"})

    assert response.headers["x-request-id"] == "demo-request_1"


def test_development_cors_is_explicit() -> None:
    with build_client() as client:
        response = client.options(
            "/health",
            headers={
                "origin": "http://localhost:3000",
                "access-control-request-method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_openapi_contract_has_a_stable_operation_id() -> None:
    schema = create_app(Settings(app_env="test")).openapi()

    operation = schema["paths"]["/health"]["get"]
    assert operation["operationId"] == "get_health"
    assert operation["tags"] == ["system"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/HealthResponse"
    }
    assert schema["components"]["schemas"]["HealthResponse"]["required"] == ["status"]
