"""Outbound-call HTTP contract and verified Twilio transport ingress."""

import re
import secrets
from datetime import UTC
from email.utils import parsedate_to_datetime
from typing import Annotated
from urllib.parse import parse_qsl
from uuid import NAMESPACE_URL, UUID, uuid5
from xml.etree.ElementTree import Element, SubElement, tostring

from fastapi import APIRouter, Depends, Request, Response, WebSocket, status
from fastapi.responses import JSONResponse
from yuno_backend.volta.errors import InvalidDomainValue
from yuno_backend.volta.telephony import (
    InboundCallError,
    InvalidOutboundCallResponseError,
    OutboundCallAllowlistError,
    OutboundCallAuthenticationError,
    OutboundCallAuthorization,
    OutboundCallAuthorizationError,
    OutboundCallIdempotencyConflict,
    OutboundCallOutcomeUncertain,
    OutboundCallProviderError,
    OutboundCallRateLimitError,
    OutboundCallRequest,
    OutboundCallStatus,
    OutboundCallStatusEvent,
    OutboundCallTimeoutError,
    RecordingMode,
)

from app.config import Settings
from app.contract_service import ContractServiceError
from app.errors import api_error_response
from app.routers.contracts import IdempotencyKey, error_responses
from app.schemas.errors import ApiErrorCode, ApiErrorResponse
from app.schemas.telephony import CreateOutboundCallRequest, OutboundCallResponse
from app.security.demo_bearer import require_demo_bearer
from app.security.realtime_origin import require_realtime_origin
from app.telephony.bridge import MediaProtocolError, bridge_media_stream
from app.telephony.service import (
    TelephonyApplication,
    get_telephony_application,
    get_websocket_telephony_application,
)
from app.telephony.signatures import verify_twilio_signature

TelephonyService = Annotated[TelephonyApplication, Depends(get_telephony_application)]

router = APIRouter(prefix="/v1", tags=["telephony"])


def _correlation_id(request: Request) -> UUID:
    request_id = getattr(request.state, "request_id", "unavailable")
    return uuid5(NAMESPACE_URL, f"volta-request:{request_id}")


def _outbound_error(request: Request, error: Exception) -> JSONResponse:
    mapping: dict[type[Exception], tuple[int, ApiErrorCode, str]] = {
        OutboundCallAuthorizationError: (
            403,
            ApiErrorCode.ACTION_NOT_AUTHORIZED,
            "The outbound call is not authorized.",
        ),
        OutboundCallAllowlistError: (
            404,
            ApiErrorCode.RESOURCE_NOT_FOUND,
            "The authorized destination is unavailable.",
        ),
        OutboundCallIdempotencyConflict: (
            409,
            ApiErrorCode.IDEMPOTENCY_KEY_REUSED,
            "The idempotency key belongs to a different request.",
        ),
        OutboundCallAuthenticationError: (
            502,
            ApiErrorCode.TELEPHONY_UNAVAILABLE,
            "The telephony provider is unavailable.",
        ),
        OutboundCallRateLimitError: (
            429,
            ApiErrorCode.RATE_LIMITED,
            "The telephony provider is temporarily rate limited.",
        ),
        OutboundCallTimeoutError: (
            504,
            ApiErrorCode.TELEPHONY_OUTCOME_UNCERTAIN,
            "The outbound call outcome is uncertain.",
        ),
        OutboundCallOutcomeUncertain: (
            503,
            ApiErrorCode.TELEPHONY_OUTCOME_UNCERTAIN,
            "The outbound call outcome is uncertain.",
        ),
        InvalidOutboundCallResponseError: (
            502,
            ApiErrorCode.TELEPHONY_UNAVAILABLE,
            "The telephony provider returned an invalid response.",
        ),
        OutboundCallProviderError: (
            502,
            ApiErrorCode.TELEPHONY_UNAVAILABLE,
            "The telephony provider is unavailable.",
        ),
    }
    code, error_code, message = mapping.get(
        type(error),
        (503, ApiErrorCode.TELEPHONY_UNAVAILABLE, "Telephony is not configured."),
    )
    return api_error_response(request, status_code=code, code=error_code, message=message)


@router.post(
    "/operations/{operation_id}/outbound-calls",
    operation_id="create_outbound_call",
    status_code=status.HTTP_201_CREATED,
    response_model=OutboundCallResponse,
    dependencies=[Depends(require_demo_bearer), Depends(require_realtime_origin)],
    responses={
        201: {"model": OutboundCallResponse, "description": "The call was accepted."},
        **error_responses(401, 403, 404, 409, 422, 429, 500),
        502: {"model": ApiErrorResponse, "description": "Provider failure."},
        503: {"model": ApiErrorResponse, "description": "Unavailable or uncertain outcome."},
        504: {"model": ApiErrorResponse, "description": "Provider timeout."},
    },
)
async def create_outbound_call(
    operation_id: UUID,
    body: CreateOutboundCallRequest,
    idempotency_key: IdempotencyKey,
    request: Request,
    application: TelephonyService,
) -> OutboundCallResponse | JSONResponse:
    try:
        call_request = OutboundCallRequest(
            operation_id=operation_id,
            call_session_id=body.call_session_id,
            correlation_id=_correlation_id(request),
            idempotency_key=idempotency_key,
            destination_label=body.destination_label,
            authorization=OutboundCallAuthorization(
                actor_id=body.authorized_by,
                authorized_at=body.authorized_at,
                ai_disclosure_required=body.ai_disclosure_required,
                recording_mode=RecordingMode(body.recording_mode),
                recording_consent_required=body.recording_consent_required,
            ),
        )
        call = await application.create_outbound_call(call_request)
    except ContractServiceError:
        raise
    except (InvalidDomainValue, ValueError):
        return api_error_response(
            request,
            status_code=422,
            code=ApiErrorCode.VALIDATION_ERROR,
            message="The outbound call request is invalid.",
        )
    except Exception as exc:
        return _outbound_error(request, exc)

    return OutboundCallResponse(
        call_session_id=call.call_session_id,
        provider_call_id=call.provider_call_id,
        status=call.status.value,
        created_at=call.created_at,
        status_updated_at=call.status_updated_at or call.created_at,
    )


async def _verified_form(request: Request) -> dict[str, str] | None:
    content_type = request.headers.get("content-type", "").partition(";")[0].strip().lower()
    if content_type != "application/x-www-form-urlencoded" or request.url.query:
        return None
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 65_536:
            return None
    try:
        pairs = parse_qsl(bytes(body).decode("utf-8"), keep_blank_values=True)
    except UnicodeDecodeError:
        return None
    settings: Settings = request.app.state.settings
    url = f"{settings.twilio_public_base_url}{request.url.path}"
    signature = request.headers.get("x-twilio-signature")
    if not verify_twilio_signature(
        url,
        pairs,
        signature,
        settings.twilio_auth_token.get_secret_value(),
    ):
        return None
    if len({name for name, _ in pairs}) != len(pairs):
        return None
    if len(pairs) > 64:
        return None
    return dict(pairs)


def _xml_response(root: Element) -> Response:
    return Response(tostring(root, encoding="unicode"), media_type="application/xml")


def _hangup_response(message: str | None = None) -> Response:
    root = Element("Response")
    if message is not None:
        SubElement(root, "Say").text = message
    SubElement(root, "Hangup")
    return _xml_response(root)


_CALL_SID = re.compile(r"^CA[0-9a-fA-F]{32}$")
_ACCOUNT_SID = re.compile(r"^AC[0-9a-fA-F]{32}$")
_E164 = re.compile(r"^\+[1-9][0-9]{7,14}$")


def _inbound_identity(parameters: dict[str, str], settings: Settings) -> tuple[str, str] | None:
    account_sid = parameters.get("AccountSid", "")
    call_sid = parameters.get("CallSid", "")
    caller = parameters.get("From", "")
    destination = parameters.get("To", "")
    expected_account_sid = settings.twilio_account_sid.get_secret_value()
    expected_destination = settings.twilio_inbound_destination_e164.get_secret_value()
    if (
        _ACCOUNT_SID.fullmatch(account_sid) is None
        or _CALL_SID.fullmatch(call_sid) is None
        or _E164.fullmatch(caller) is None
        or _E164.fullmatch(destination) is None
        or not secrets.compare_digest(account_sid, expected_account_sid)
        or not expected_destination
        or not secrets.compare_digest(destination, expected_destination)
    ):
        return None
    for label, configured_caller in settings.twilio_inbound_caller_allowlist.items():
        if secrets.compare_digest(caller, configured_caller):
            return label, call_sid
    return "", call_sid


@router.post("/telephony/twilio/inbound/voice", include_in_schema=False)
async def twilio_inbound_voice(request: Request) -> Response:
    parameters = await _verified_form(request)
    if parameters is None:
        return Response(status_code=403)
    identity = _inbound_identity(parameters, request.app.state.settings)
    if identity is None:
        return Response(status_code=403)
    caller_label, provider_call_id = identity
    if not caller_label:
        return _hangup_response()
    application = get_telephony_application(request)
    try:
        await application.accept_inbound_call(
            caller_label, provider_call_id, _correlation_id(request)
        )
    except (InboundCallError, RuntimeError, ValueError):
        return _hangup_response()

    root = Element("Response")
    SubElement(root, "Say").text = (
        "This is Volta, an artificial intelligence assistant. "
        "With your consent, this call will be recorded for private demo evidence."
    )
    gather = SubElement(
        root,
        "Gather",
        {
            "action": (
                f"{request.app.state.settings.twilio_public_base_url}"
                "/v1/telephony/twilio/inbound/consent"
            ),
            "input": "dtmf",
            "method": "POST",
            "numDigits": "1",
            "timeout": "5",
        },
    )
    SubElement(gather, "Say").text = "Press 1 to consent and continue."
    SubElement(root, "Hangup")
    return _xml_response(root)


@router.post("/telephony/twilio/inbound/consent", include_in_schema=False)
async def twilio_inbound_consent(request: Request) -> Response:
    parameters = await _verified_form(request)
    if parameters is None:
        return Response(status_code=403)
    identity = _inbound_identity(parameters, request.app.state.settings)
    if identity is None:
        return Response(status_code=403)
    caller_label, provider_call_id = identity
    if not caller_label or parameters.get("Digits") != "1":
        return _hangup_response("Consent was not received. The call will end.")
    application = get_telephony_application(request)
    try:
        binding = await application.record_inbound_consent(
            caller_label, provider_call_id, _correlation_id(request)
        )
    except (InboundCallError, RuntimeError, ValueError):
        return _hangup_response()

    root = Element("Response")
    connect = SubElement(root, "Connect")
    stream = SubElement(
        connect,
        "Stream",
        {"url": request.app.state.settings.twilio_media_ws_url},
    )
    SubElement(stream, "Parameter", {"name": "binding", "value": binding.stream_token})
    return _xml_response(root)


@router.post("/telephony/twilio/voice", include_in_schema=False)
async def twilio_voice(request: Request, application: TelephonyService) -> Response:
    parameters = await _verified_form(request)
    if parameters is None:
        return Response(status_code=403)
    provider_call_id = parameters.get("CallSid", "")
    if parameters.get("AccountSid") != application.twilio_account_sid:
        return Response(status_code=403)
    binding = await application.binding_for_voice(provider_call_id)
    if binding is None:
        return Response(status_code=404)
    root = Element("Response")
    SubElement(root, "Say").text = "This is Volta, an AI assistant. This call is not recorded."
    gather = SubElement(
        root,
        "Gather",
        {
            "action": (
                f"{request.app.state.settings.twilio_public_base_url}/v1/telephony/twilio/consent"
            ),
            "input": "dtmf",
            "method": "POST",
            "numDigits": "1",
        },
    )
    SubElement(gather, "Say").text = "Press 1 to continue."
    SubElement(root, "Hangup")
    return _xml_response(root)


@router.post("/telephony/twilio/consent", include_in_schema=False)
async def twilio_consent(request: Request, application: TelephonyService) -> Response:
    parameters = await _verified_form(request)
    if parameters is None:
        return Response(status_code=403)
    if parameters.get("AccountSid") != application.twilio_account_sid:
        return Response(status_code=403)
    binding = await application.binding_for_voice(parameters.get("CallSid", ""))
    if binding is None or parameters.get("Digits") != "1":
        root = Element("Response")
        SubElement(root, "Say").text = "Consent was not received. The call will end."
        SubElement(root, "Hangup")
        return _xml_response(root)
    root = Element("Response")
    connect = SubElement(root, "Connect")
    stream = SubElement(
        connect,
        "Stream",
        {"url": request.app.state.settings.twilio_media_ws_url},
    )
    SubElement(stream, "Parameter", {"name": "binding", "value": binding.stream_token})
    return _xml_response(root)


_TWILIO_STATUS = {
    "completed": OutboundCallStatus.COMPLETED,
    "busy": OutboundCallStatus.BUSY,
    "failed": OutboundCallStatus.FAILED,
    "no-answer": OutboundCallStatus.NO_ANSWER,
    "canceled": OutboundCallStatus.CANCELED,
}


@router.post("/telephony/twilio/status", include_in_schema=False)
async def twilio_status(request: Request, application: TelephonyService) -> Response:
    parameters = await _verified_form(request)
    if parameters is None:
        return Response(status_code=403)
    if parameters.get("AccountSid") != application.twilio_account_sid:
        return Response(status_code=403)
    normalized_status = _TWILIO_STATUS.get(parameters.get("CallStatus", ""))
    if normalized_status is None:
        return Response(status_code=204)
    try:
        sequence = int(parameters.get("SequenceNumber", "0"))
        observed_at = parsedate_to_datetime(parameters.get("Timestamp", ""))
        if observed_at.tzinfo is None:
            raise ValueError("Twilio timestamp must include a timezone")
        call_sid = parameters["CallSid"]
        event = OutboundCallStatusEvent(
            provider_event_id=f"{call_sid}:{sequence}:{normalized_status.value}",
            provider_call_id=call_sid,
            status=normalized_status,
            sequence_number=sequence,
            observed_at=observed_at.astimezone(UTC),
        )
    except (KeyError, TypeError, ValueError, InvalidDomainValue):
        return Response(status_code=422)
    await application.observe_status(event)
    return Response(status_code=204)


@router.websocket("/telephony/twilio/media")
async def twilio_media(websocket: WebSocket) -> None:
    settings: Settings = websocket.app.state.settings
    if not verify_twilio_signature(
        settings.twilio_media_ws_url,
        {},
        websocket.headers.get("x-twilio-signature"),
        settings.twilio_auth_token.get_secret_value(),
    ):
        await websocket.close(code=1008)
        return
    application = get_websocket_telephony_application(websocket)
    async with websocket.app.state.twilio_media_lock:
        if websocket.app.state.twilio_media_active:
            await websocket.close(code=1013)
            return
        websocket.app.state.twilio_media_active = True
    try:
        await websocket.accept()
        try:
            await bridge_media_stream(websocket, application)
        except (MediaProtocolError, ValueError):
            await websocket.close(code=1008)
        except Exception:
            await websocket.close(code=1011)
    finally:
        async with websocket.app.state.twilio_media_lock:
            websocket.app.state.twilio_media_active = False
        try:
            await websocket.close(code=1000)
        except RuntimeError:
            pass
