"""Central translation to the stable, non-sensitive API error envelope."""

from uuid import UUID

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.contract_service import ContractServiceError
from app.schemas.errors import ApiErrorCode, ApiErrorResponse, FieldIssue


def request_id_from(request: Request) -> str:
    return getattr(request.state, "request_id", "unavailable")


def api_error_response(
    request: Request,
    *,
    status_code: int,
    code: ApiErrorCode,
    message: str,
    field_issues: list[FieldIssue] | None = None,
    resource_id: UUID | None = None,
    current_draft_version: int | None = None,
    current_operation_version: int | None = None,
) -> JSONResponse:
    body = ApiErrorResponse(
        code=code,
        message=message,
        request_id=request_id_from(request),
        field_issues=field_issues,
        resource_id=resource_id,
        current_draft_version=current_draft_version,
        current_operation_version=current_operation_version,
    )
    headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(body),
        headers=headers,
    )


async def contract_service_error_handler(
    request: Request,
    error: ContractServiceError,
) -> JSONResponse:
    resource_id: UUID | None = None
    if error.resource_id is not None:
        try:
            resource_id = UUID(error.resource_id)
        except ValueError:
            resource_id = None
    return api_error_response(
        request,
        status_code=error.status_code,
        code=error.code,
        message=error.safe_message,
        field_issues=error.field_issues,
        resource_id=resource_id,
        current_draft_version=error.current_draft_version,
        current_operation_version=error.current_operation_version,
    )


async def validation_error_handler(
    request: Request,
    error: RequestValidationError,
) -> JSONResponse:
    issues = [
        FieldIssue(
            field=".".join(str(part) for part in issue["loc"]),
            message=issue["msg"],
            code=issue["type"],
        )
        for issue in error.errors()
    ]
    return api_error_response(
        request,
        status_code=422,
        code=ApiErrorCode.VALIDATION_ERROR,
        message="The request did not satisfy the public contract.",
        field_issues=issues,
    )


async def unexpected_error_handler(request: Request, error: Exception) -> JSONResponse:
    del error
    return api_error_response(
        request,
        status_code=500,
        code=ApiErrorCode.INTERNAL_ERROR,
        message="The request could not be completed.",
    )
