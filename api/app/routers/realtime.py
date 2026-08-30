"""Authorized boundary for issuing one short-lived Realtime credential."""

from typing import Any

from fastapi import APIRouter, Depends, Response, status

from app.realtime_service import (
    RealtimeClientSecretServiceDep,
)
from app.schemas.errors import ApiErrorResponse
from app.schemas.realtime import RealtimeClientSecretResponse
from app.security.demo_bearer import require_demo_bearer
from app.security.realtime_origin import require_realtime_origin

REQUEST_ID_HEADER = {
    "description": "Correlation identifier preserved or assigned by the API.",
    "schema": {"type": "string", "minLength": 1, "maxLength": 128},
}
RETRY_AFTER_HEADER = {
    "description": "Whole seconds until credential issuance can be retried.",
    "schema": {"type": "integer", "minimum": 1},
}
CACHE_CONTROL_HEADER = {
    "description": "Prevents storage of credentials and route-owned errors.",
    "schema": {"type": "string", "enum": ["no-store, private, max-age=0"]},
}
PRAGMA_HEADER = {
    "description": "Legacy cache prevention for credential-bearing responses.",
    "schema": {"type": "string", "enum": ["no-cache"]},
}
WWW_AUTHENTICATE_HEADER = {
    "description": "Bearer authentication challenge for a missing or invalid credential.",
    "schema": {"type": "string", "enum": ["Bearer"]},
}


def realtime_responses() -> dict[int, dict[str, Any]]:
    common_headers = {
        "X-Request-ID": REQUEST_ID_HEADER,
        "Cache-Control": CACHE_CONTROL_HEADER,
        "Pragma": PRAGMA_HEADER,
    }
    descriptions = {
        401: "Authentication is missing or invalid.",
        403: "The request origin or actor is not authorized.",
        429: "The configured demo traffic boundary was exceeded.",
        500: "An unexpected failure was translated safely.",
        502: "Realtime credential issuance is temporarily unavailable.",
    }
    return {
        201: {
            "description": "One short-lived, narrowly scoped Realtime credential.",
            "headers": common_headers,
        },
        **{
            code: {
                "model": ApiErrorResponse,
                "description": description,
                "headers": {
                    **common_headers,
                    **({"WWW-Authenticate": WWW_AUTHENTICATE_HEADER} if code == 401 else {}),
                    **({"Retry-After": RETRY_AFTER_HEADER} if code == 429 else {}),
                },
            }
            for code, description in descriptions.items()
        },
    }


router = APIRouter(
    prefix="/v1/realtime",
    tags=["realtime"],
    dependencies=[Depends(require_demo_bearer), Depends(require_realtime_origin)],
)

@router.post(
    "/client-secrets",
    operation_id="create_realtime_client_secret",
    status_code=status.HTTP_201_CREATED,
    responses=realtime_responses(),
)
async def create_realtime_client_secret(
    response: Response,
    service: RealtimeClientSecretServiceDep,
) -> RealtimeClientSecretResponse:
    result = await service.issue()
    response.headers["Cache-Control"] = "no-store, private, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return result
