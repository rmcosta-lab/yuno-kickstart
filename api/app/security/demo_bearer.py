"""Configured bearer authentication for the synthetic demo actor."""

import hmac
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings
from app.contract_service import ContractServiceError
from app.schemas.errors import ApiErrorCode

_bearer = HTTPBearer(
    auto_error=False,
    bearerFormat="opaque demo token",
    description="Configured demo bearer token. No token value is published.",
)


def settings_from_request(request: Request) -> Settings:
    return request.app.state.settings


def require_demo_bearer(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(settings_from_request)],
) -> None:
    authorization = request.headers.get("authorization")
    if authorization is None:
        raise ContractServiceError(
            status_code=401,
            code=ApiErrorCode.AUTHENTICATION_REQUIRED,
            message="Bearer authentication is required.",
        )

    if credentials is None:
        raise ContractServiceError(
            status_code=401,
            code=ApiErrorCode.AUTHENTICATION_INVALID,
            message="Bearer authentication is invalid.",
        )

    configured_token = settings.volta_demo_bearer_token.get_secret_value()
    valid = bool(configured_token) and hmac.compare_digest(
        credentials.credentials.encode("utf-8"),
        configured_token.encode("utf-8"),
    )
    if credentials.scheme.lower() != "bearer" or not valid:
        raise ContractServiceError(
            status_code=401,
            code=ApiErrorCode.AUTHENTICATION_INVALID,
            message="Bearer authentication is invalid.",
        )
