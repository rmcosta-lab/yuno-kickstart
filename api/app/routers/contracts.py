"""Contract-only declarations for the complete Volta P0 browser surface."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, status
from pydantic import BaseModel

from app.contract_service import ContractResult, ContractService, JsonValue, get_contract_service
from app.schemas.contracts import (
    AcknowledgeNotificationRequest,
    ApproveOperationRequest,
    AuditTimelineResponse,
    CallBriefResponse,
    CommitmentEvidenceResponse,
    CommitmentResponse,
    CoordinatorNotificationResponse,
    CreateCallBriefRequest,
    CreateCommitmentEvidenceRequest,
    CreateCommitmentRequest,
    CreateEscalationRequest,
    CreateOperationDraftRequest,
    CreateQuoteRequest,
    CreateSimulatedRecapRequest,
    EscalationResponse,
    NegotiationResponse,
    OperationDraftResponse,
    OperationResponse,
    QuoteResponse,
    RecoverySimulationResponse,
    ReplaceMandateRequest,
    StartInboundSimulationRequest,
    StartNegotiationRequest,
    WrittenRecapResponse,
)
from app.schemas.errors import ApiErrorResponse
from app.security.demo_bearer import require_demo_bearer

IdempotencyKey = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
        pattern=r"^[\x20-\x7E]+$",
        description="Printable ASCII key reused for one logical mutation.",
    ),
]
Service = Annotated[ContractService, Depends(get_contract_service)]

REQUEST_ID_HEADER = {
    "description": "Correlation identifier preserved or assigned by the API.",
    "schema": {"type": "string", "minLength": 1, "maxLength": 128},
}
REPLAY_HEADER = {
    "description": "True only when an injected application service replays the original result.",
    "schema": {"type": "string", "enum": ["true"]},
}
RETRY_AFTER_HEADER = {
    "description": "Whole seconds until the authorized mutation window can accept traffic.",
    "schema": {"type": "integer", "minimum": 1},
}
AUDIO_CACHE_CONTROL_HEADER = {
    "description": "Private evidence must not be stored by browsers or intermediaries.",
    "schema": {"type": "string", "enum": ["private, no-store"]},
}
AUDIO_PRAGMA_HEADER = {
    "description": "Compatibility no-cache directive for private evidence.",
    "schema": {"type": "string", "enum": ["no-cache"]},
}
AUDIO_NOSNIFF_HEADER = {
    "description": "Prevents media type sniffing.",
    "schema": {"type": "string", "enum": ["nosniff"]},
}


def error_responses(*status_codes: int) -> dict[int, dict[str, Any]]:
    descriptions = {
        401: "Authentication is missing or invalid.",
        403: "The authenticated actor lacks authority.",
        404: "The referenced resource was not found.",
        409: "The request conflicts with current state or idempotency history.",
        413: "The requested evidence exceeds the demo playback limit.",
        422: "The request does not satisfy the public contract.",
        429: "The configured demo traffic boundary was exceeded.",
        500: "An unexpected failure was translated safely.",
        501: "The contract has no application service wired yet.",
    }
    return {
        code: {
            "model": ApiErrorResponse,
            "description": descriptions[code],
            "headers": {
                "X-Request-ID": REQUEST_ID_HEADER,
                **({"Retry-After": RETRY_AFTER_HEADER} if code == 429 else {}),
            },
        }
        for code in status_codes
    }


def mutation_responses(
    success_status: int,
    *route_status_codes: int,
) -> dict[int, dict[str, Any]]:
    return {
        success_status: {
            "description": "Typed mutation result.",
            "headers": {
                "X-Request-ID": REQUEST_ID_HEADER,
                "Idempotency-Replayed": REPLAY_HEADER,
            },
        },
        **error_responses(401, 422, 429, 500, 501, *route_status_codes),
    }


def query_responses(*route_status_codes: int) -> dict[int, dict[str, Any]]:
    return {
        200: {
            "description": "Typed query result.",
            "headers": {"X-Request-ID": REQUEST_ID_HEADER},
        },
        **error_responses(401, 422, 500, 501, *route_status_codes),
    }


router = APIRouter(
    prefix="/v1",
    tags=["volta"],
    dependencies=[Depends(require_demo_bearer)],
)


def payload_for(body: BaseModel | None = None, **values: object) -> dict[str, JsonValue]:
    payload: dict[str, JsonValue] = {}
    if body is not None:
        payload["body"] = body.model_dump(mode="json")
    for key, value in values.items():
        if isinstance(value, UUID):
            payload[key] = str(value)
        else:
            payload[key] = value  # type: ignore[assignment]
    return payload


def apply_replay_header(response: Response, result: ContractResult) -> None:
    if result.idempotency_replayed:
        response.headers["Idempotency-Replayed"] = "true"


async def execute_mutation(
    service: ContractService,
    contract_operation_id: str,
    body: BaseModel,
    idempotency_key: str,
    response: Response,
    **path_values: object,
) -> JsonValue:
    result = await service.execute(
        contract_operation_id,
        payload_for(body, **path_values),
        idempotency_key,
    )
    apply_replay_header(response, result)
    return result.payload


@router.post(
    "/operation-drafts",
    operation_id="create_operation_draft",
    status_code=status.HTTP_201_CREATED,
    response_model=OperationDraftResponse,
    responses=mutation_responses(201, 403, 409),
)
async def create_operation_draft(
    body: CreateOperationDraftRequest,
    idempotency_key: IdempotencyKey,
    response: Response,
    service: Service,
) -> JsonValue:
    return await execute_mutation(
        service,
        "create_operation_draft",
        body,
        idempotency_key,
        response,
    )


@router.post(
    "/operations",
    operation_id="approve_operation",
    status_code=status.HTTP_201_CREATED,
    response_model=OperationResponse,
    responses=mutation_responses(201, 403, 404, 409),
)
async def approve_operation(
    body: ApproveOperationRequest,
    idempotency_key: IdempotencyKey,
    response: Response,
    service: Service,
) -> JsonValue:
    return await execute_mutation(service, "approve_operation", body, idempotency_key, response)


@router.get(
    "/operations/{operation_id}",
    operation_id="get_operation",
    response_model=OperationResponse,
    responses=query_responses(403, 404),
)
async def get_operation(operation_id: UUID, service: Service) -> JsonValue:
    result = await service.execute("get_operation", payload_for(operation_id=operation_id), None)
    return result.payload


@router.post(
    "/operations/{operation_id}/negotiations",
    operation_id="start_negotiation",
    status_code=status.HTTP_201_CREATED,
    response_model=NegotiationResponse,
    responses=mutation_responses(201, 403, 404, 409),
)
async def start_negotiation(
    operation_id: UUID,
    body: StartNegotiationRequest,
    idempotency_key: IdempotencyKey,
    response: Response,
    service: Service,
) -> JsonValue:
    return await execute_mutation(
        service, "start_negotiation", body, idempotency_key, response, operation_id=operation_id
    )


@router.post(
    "/calls/{call_id}/quotes",
    operation_id="record_quote",
    status_code=status.HTTP_201_CREATED,
    response_model=QuoteResponse,
    responses=mutation_responses(201, 403, 404, 409),
)
async def record_quote(
    call_id: UUID,
    body: CreateQuoteRequest,
    idempotency_key: IdempotencyKey,
    response: Response,
    service: Service,
) -> JsonValue:
    return await execute_mutation(
        service,
        "record_quote",
        body,
        idempotency_key,
        response,
        call_id=call_id,
    )


@router.post(
    "/calls/{call_id}/evidence",
    operation_id="attach_commitment_evidence",
    status_code=status.HTTP_201_CREATED,
    response_model=CommitmentEvidenceResponse,
    responses=mutation_responses(201, 403, 404, 409),
)
async def attach_commitment_evidence(
    call_id: UUID,
    body: CreateCommitmentEvidenceRequest,
    idempotency_key: IdempotencyKey,
    response: Response,
    service: Service,
) -> JsonValue:
    return await execute_mutation(
        service, "attach_commitment_evidence", body, idempotency_key, response, call_id=call_id
    )


@router.get(
    "/evidence/{evidence_id}/audio",
    operation_id="get_evidence_audio",
    response_class=Response,
    responses={
        200: {
            "description": "Private RIFF/WAVE evidence bytes.",
            "content": {
                "audio/wav": {
                    "schema": {"type": "string", "format": "binary"},
                }
            },
            "headers": {
                "X-Request-ID": REQUEST_ID_HEADER,
                "Cache-Control": AUDIO_CACHE_CONTROL_HEADER,
                "Pragma": AUDIO_PRAGMA_HEADER,
                "X-Content-Type-Options": AUDIO_NOSNIFF_HEADER,
            },
        },
        **error_responses(401, 403, 404, 413, 422, 500),
    },
)
async def get_evidence_audio(evidence_id: UUID, service: Service) -> Response:
    audio = await service.get_evidence_audio(evidence_id)
    return Response(
        content=audio.content,
        media_type=audio.media_type,
        headers={
            "Cache-Control": "private, no-store",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
            "Content-Length": str(audio.content_length),
        },
    )


@router.post(
    "/calls/{call_id}/commitments",
    operation_id="create_candidate_commitment",
    status_code=status.HTTP_201_CREATED,
    response_model=CommitmentResponse,
    responses=mutation_responses(201, 403, 404, 409),
)
async def create_candidate_commitment(
    call_id: UUID,
    body: CreateCommitmentRequest,
    idempotency_key: IdempotencyKey,
    response: Response,
    service: Service,
) -> JsonValue:
    return await execute_mutation(
        service, "create_candidate_commitment", body, idempotency_key, response, call_id=call_id
    )


@router.post(
    "/calls/{call_id}/recaps",
    operation_id="create_simulated_recap",
    status_code=status.HTTP_201_CREATED,
    response_model=WrittenRecapResponse,
    responses=mutation_responses(201, 403, 404, 409),
)
async def create_simulated_recap(
    call_id: UUID,
    body: CreateSimulatedRecapRequest,
    idempotency_key: IdempotencyKey,
    response: Response,
    service: Service,
) -> JsonValue:
    return await execute_mutation(
        service, "create_simulated_recap", body, idempotency_key, response, call_id=call_id
    )


@router.post(
    "/calls/{call_id}/briefs",
    operation_id="create_call_brief",
    status_code=status.HTTP_201_CREATED,
    response_model=CallBriefResponse,
    responses=mutation_responses(201, 403, 404, 409),
)
async def create_call_brief(
    call_id: UUID,
    body: CreateCallBriefRequest,
    idempotency_key: IdempotencyKey,
    response: Response,
    service: Service,
) -> JsonValue:
    return await execute_mutation(
        service,
        "create_call_brief",
        body,
        idempotency_key,
        response,
        call_id=call_id,
    )


@router.post(
    "/operations/{operation_id}/inbound-simulations",
    operation_id="start_inbound_simulation",
    status_code=status.HTTP_201_CREATED,
    response_model=RecoverySimulationResponse,
    responses=mutation_responses(201, 403, 404, 409),
)
async def start_inbound_simulation(
    operation_id: UUID,
    body: StartInboundSimulationRequest,
    idempotency_key: IdempotencyKey,
    response: Response,
    service: Service,
) -> JsonValue:
    return await execute_mutation(
        service,
        "start_inbound_simulation",
        body,
        idempotency_key,
        response,
        operation_id=operation_id,
    )


@router.post(
    "/operations/{operation_id}/mandates",
    operation_id="replace_mandate",
    status_code=status.HTTP_201_CREATED,
    response_model=OperationResponse,
    responses=mutation_responses(201, 403, 404, 409),
)
async def replace_mandate(
    operation_id: UUID,
    body: ReplaceMandateRequest,
    idempotency_key: IdempotencyKey,
    response: Response,
    service: Service,
) -> JsonValue:
    return await execute_mutation(
        service, "replace_mandate", body, idempotency_key, response, operation_id=operation_id
    )


@router.post(
    "/calls/{call_id}/escalations",
    operation_id="create_escalation",
    status_code=status.HTTP_201_CREATED,
    response_model=EscalationResponse,
    responses=mutation_responses(201, 403, 404, 409),
)
async def create_escalation(
    call_id: UUID,
    body: CreateEscalationRequest,
    idempotency_key: IdempotencyKey,
    response: Response,
    service: Service,
) -> JsonValue:
    return await execute_mutation(
        service, "create_escalation", body, idempotency_key, response, call_id=call_id
    )


@router.post(
    "/notifications/{notification_id}/acknowledgements",
    operation_id="acknowledge_notification",
    response_model=CoordinatorNotificationResponse,
    responses=mutation_responses(200, 403, 404, 409),
)
async def acknowledge_notification(
    notification_id: UUID,
    body: AcknowledgeNotificationRequest,
    idempotency_key: IdempotencyKey,
    response: Response,
    service: Service,
) -> JsonValue:
    return await execute_mutation(
        service,
        "acknowledge_notification",
        body,
        idempotency_key,
        response,
        notification_id=notification_id,
    )


@router.get(
    "/operations/{operation_id}/audit",
    operation_id="get_operation_audit",
    response_model=AuditTimelineResponse,
    responses=query_responses(403, 404),
)
async def get_operation_audit(
    operation_id: UUID,
    service: Service,
    cursor: Annotated[str | None, Query(min_length=1, max_length=512)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> JsonValue:
    result = await service.execute(
        "get_operation_audit",
        payload_for(operation_id=operation_id, cursor=cursor, limit=limit),
        None,
    )
    return result.payload
