"""Injectable transport-to-application boundary used by contract-only routes."""

from dataclasses import dataclass
from typing import Protocol

from app.schemas.errors import ApiErrorCode, FieldIssue

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]


@dataclass(frozen=True, slots=True)
class ContractResult:
    payload: JsonValue
    idempotency_replayed: bool = False


class ContractService(Protocol):
    async def execute(
        self,
        operation_id: str,
        payload: dict[str, JsonValue],
        idempotency_key: str | None,
    ) -> ContractResult: ...


class ContractServiceError(Exception):
    """Safe public failure emitted by a later application-service adapter."""

    def __init__(
        self,
        *,
        status_code: int,
        code: ApiErrorCode,
        message: str,
        field_issues: list[FieldIssue] | None = None,
        resource_id: str | None = None,
        current_operation_version: int | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.safe_message = message
        self.field_issues = field_issues
        self.resource_id = resource_id
        self.current_operation_version = current_operation_version


class UnimplementedContractService:
    async def execute(
        self,
        operation_id: str,
        payload: dict[str, JsonValue],
        idempotency_key: str | None,
    ) -> ContractResult:
        del operation_id, payload, idempotency_key
        raise ContractServiceError(
            status_code=501,
            code=ApiErrorCode.CONTRACT_NOT_IMPLEMENTED,
            message="This contract is not connected to an application service yet.",
        )


_default_service = UnimplementedContractService()


def get_contract_service() -> ContractService:
    return _default_service
