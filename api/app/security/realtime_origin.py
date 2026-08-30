"""Exact browser-origin authorization for credential issuance."""

from fastapi import Request

from app.contract_service import ContractServiceError
from app.schemas.errors import ApiErrorCode


def require_realtime_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin is None or origin not in request.app.state.settings.cors_origins:
        raise ContractServiceError(
            status_code=403,
            code=ApiErrorCode.ACTION_NOT_AUTHORIZED,
            message="The request origin is not authorized.",
        )
