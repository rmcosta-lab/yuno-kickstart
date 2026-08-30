from __future__ import annotations

import ast
import asyncio
import base64
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qsl
from uuid import UUID

import httpx
import pytest
from yuno_backend.integrations.twilio import (
    TwilioDestinationAllowlist,
    TwilioOutboundCallConfig,
    TwilioOutboundCallGateway,
    map_twilio_call_status,
)
from yuno_backend.volta.telephony import (
    OutboundCall,
    OutboundCallAllowlistError,
    OutboundCallAttempt,
    OutboundCallAttemptReservation,
    OutboundCallAttemptState,
    OutboundCallAuthenticationError,
    OutboundCallAuthorization,
    OutboundCallAuthorizationError,
    OutboundCallFailure,
    OutboundCallFailureCategory,
    OutboundCallIdempotencyConflict,
    OutboundCallOutcomeUncertain,
    OutboundCallProviderError,
    OutboundCallRateLimitError,
    OutboundCallRequest,
    OutboundCallStatus,
    OutboundCallTimeoutError,
    OutboundCallUncertainReason,
    OutboundCallUncertainState,
    RecordingMode,
    outbound_call_request_fingerprint,
)

NOW = datetime(2026, 8, 30, 12, tzinfo=UTC)
ACCOUNT_SID = "AC" + "a" * 32
API_KEY_SID = "SK" + "b" * 32
API_SECRET = "private-api-secret-marker"
CALL_SID = "CA" + "c" * 32
OPERATION_ID = UUID("00000000-0000-4000-8000-000000000018")
CALL_SESSION_ID = UUID("00000000-0000-4000-8000-000000000118")
CORRELATION_ID = UUID("00000000-0000-4000-8000-000000000218")
LABEL = "AUTHORIZED_TEST_A"


def _number(digit: str) -> str:
    return "+" + digit * 11


class FixedClock:
    def now(self) -> datetime:
        return NOW


class MemoryAttemptStore:
    def __init__(self) -> None:
        self.records: dict[str, OutboundCallAttempt] = {}
        self.lock = asyncio.Lock()
        self.reserve_count = 0
        self.complete_count = 0
        self.uncertain_count = 0
        self.failure_count = 0

    async def reserve(
        self, attempt: OutboundCallAttempt
    ) -> OutboundCallAttemptReservation:
        async with self.lock:
            self.reserve_count += 1
            current = self.records.get(attempt.idempotency_key)
            if current is not None:
                return OutboundCallAttemptReservation(attempt=current, created=False)
            self.records[attempt.idempotency_key] = attempt
            return OutboundCallAttemptReservation(attempt=attempt, created=True)

    async def complete(
        self,
        idempotency_key: str,
        request_fingerprint: str,
        result: OutboundCall,
        completed_at: datetime,
    ) -> OutboundCallAttempt:
        async with self.lock:
            current = self.records[idempotency_key]
            assert current.request_fingerprint == request_fingerprint
            updated = replace(
                current,
                state=OutboundCallAttemptState.SUCCEEDED,
                result=result,
                uncertainty=None,
                failure=None,
                updated_at=completed_at,
            )
            self.records[idempotency_key] = updated
            self.complete_count += 1
            return updated

    async def mark_uncertain(
        self,
        idempotency_key: str,
        request_fingerprint: str,
        uncertainty: OutboundCallUncertainState,
    ) -> OutboundCallAttempt:
        async with self.lock:
            current = self.records[idempotency_key]
            assert current.request_fingerprint == request_fingerprint
            updated = replace(
                current,
                state=OutboundCallAttemptState.UNCERTAIN,
                result=None,
                uncertainty=uncertainty,
                failure=None,
                updated_at=uncertainty.occurred_at,
            )
            self.records[idempotency_key] = updated
            self.uncertain_count += 1
            return updated

    async def fail(
        self,
        idempotency_key: str,
        request_fingerprint: str,
        failure: OutboundCallFailure,
    ) -> OutboundCallAttempt:
        async with self.lock:
            current = self.records[idempotency_key]
            assert current.request_fingerprint == request_fingerprint
            updated = replace(
                current,
                state=OutboundCallAttemptState.FAILED,
                result=None,
                uncertainty=None,
                failure=failure,
                updated_at=failure.occurred_at,
            )
            self.records[idempotency_key] = updated
            self.failure_count += 1
            return updated


class TerminalStoreFailure(RuntimeError):
    pass


class FailingTerminalStore(MemoryAttemptStore):
    def __init__(self, operation: str) -> None:
        super().__init__()
        self.operation = operation
        self.terminal_calls = 0

    async def complete(
        self,
        idempotency_key: str,
        request_fingerprint: str,
        result: OutboundCall,
        completed_at: datetime,
    ) -> OutboundCallAttempt:
        if self.operation == "complete":
            self.terminal_calls += 1
            raise TerminalStoreFailure("private database complete detail")
        return await super().complete(
            idempotency_key, request_fingerprint, result, completed_at
        )

    async def mark_uncertain(
        self,
        idempotency_key: str,
        request_fingerprint: str,
        uncertainty: OutboundCallUncertainState,
    ) -> OutboundCallAttempt:
        if self.operation == "mark_uncertain":
            self.terminal_calls += 1
            raise TerminalStoreFailure("private database uncertainty detail")
        return await super().mark_uncertain(
            idempotency_key, request_fingerprint, uncertainty
        )

    async def fail(
        self,
        idempotency_key: str,
        request_fingerprint: str,
        failure: OutboundCallFailure,
    ) -> OutboundCallAttempt:
        if self.operation == "fail":
            self.terminal_calls += 1
            raise TerminalStoreFailure("private database failure detail")
        return await super().fail(idempotency_key, request_fingerprint, failure)


def _config(**overrides: object) -> TwilioOutboundCallConfig:
    values: dict[str, object] = {
        "account_sid": ACCOUNT_SID,
        "api_key_sid": API_KEY_SID,
        "api_key_secret": API_SECRET,
        "from_e164": _number("1"),
        "instruction_url": "https://voice.example.test/twilio/instructions",
        "status_callback_url": "https://voice.example.test/twilio/status",
    }
    values.update(overrides)
    return TwilioOutboundCallConfig(**values)  # type: ignore[arg-type]


def _request(**overrides: object) -> OutboundCallRequest:
    values: dict[str, object] = {
        "operation_id": OPERATION_ID,
        "call_session_id": CALL_SESSION_ID,
        "correlation_id": CORRELATION_ID,
        "idempotency_key": "twilio-call-001",
        "destination_label": LABEL,
        "authorization": OutboundCallAuthorization(
            actor_id="operator_01",
            authorized_at=NOW - timedelta(seconds=10),
            ai_disclosure_required=True,
            recording_mode=RecordingMode.DISABLED,
            recording_consent_required=False,
        ),
    }
    values.update(overrides)
    return OutboundCallRequest(**values)  # type: ignore[arg-type]


def _gateway(
    handler: object,
    *,
    store: MemoryAttemptStore | None = None,
    config: TwilioOutboundCallConfig | None = None,
    delay: object | None = None,
) -> tuple[TwilioOutboundCallGateway, httpx.AsyncClient, MemoryAttemptStore]:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))  # type: ignore[arg-type]
    attempt_store = store or MemoryAttemptStore()
    kwargs = {} if delay is None else {"delay": delay}
    gateway = TwilioOutboundCallGateway(
        client,
        config or _config(),
        TwilioDestinationAllowlist({LABEL: _number("2")}),
        attempt_store,
        FixedClock(),
        **kwargs,  # type: ignore[arg-type]
    )
    return gateway, client, attempt_store


def _success(status: str = "queued") -> httpx.Response:
    return httpx.Response(201, json={"sid": CALL_SID, "status": status})


def test_config_and_allowlist_are_immutable_redacted_and_official() -> None:
    config = _config()
    allowlist = TwilioDestinationAllowlist({LABEL: _number("2")})

    rendered = repr(config) + repr(allowlist)
    assert ACCOUNT_SID not in rendered
    assert API_KEY_SID not in rendered
    assert API_SECRET not in rendered
    assert _number("1") not in rendered
    assert _number("2") not in rendered
    assert config.instruction_url not in rendered
    assert config.status_callback_url not in rendered
    assert config.create_call_url == (
        "https://api.twilio.com/2010-04-01/Accounts/" f"{ACCOUNT_SID}/Calls.json"
    )
    assert allowlist.resolve(LABEL) == _number("2")
    with pytest.raises(FrozenInstanceError):
        config.timeout_seconds = 1  # type: ignore[misc]


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        ({"account_sid": "ACbad"}, "Account SID"),
        ({"api_key_sid": "SKbad"}, "API key SID"),
        ({"api_key_secret": ""}, "secret"),
        ({"api_key_secret": "x" * 257}, "secret"),
        ({"from_e164": "not-a-number"}, "E.164"),
        ({"instruction_url": "http://voice.example.test/path"}, "HTTPS"),
        ({"instruction_url": "https://127.0.0.1/path"}, "HTTPS"),
        ({"instruction_url": "https://intranet/path"}, "HTTPS"),
        ({"status_callback_url": "https://user:pass@example.test/path"}, "HTTPS"),
        ({"status_callback_url": "https://bad_host.example.test/path"}, "HTTPS"),
        ({"timeout_seconds": float("inf")}, "timeout"),
        ({"max_attempts": 4}, "max_attempts"),
        ({"backoff_seconds": ()}, "backoff"),
        ({"authorization_max_age_seconds": 0}, "authorization age"),
    ],
)
def test_config_fails_closed(overrides: dict[str, object], match: str) -> None:
    with pytest.raises(ValueError, match=match):
        _config(**overrides)


def test_adapter_imports_no_api_frontend_or_provider_sdk() -> None:
    root = Path(__file__).parents[4] / "src" / "yuno_backend" / "integrations" / "twilio"
    imported: list[str] = []
    for source in root.glob("*.py"):
        for node in ast.walk(ast.parse(source.read_text())):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
    forbidden = {"api", "frontend", "fastapi", "twilio"}
    assert not [name for name in imported if name.split(".")[0] in forbidden]


@pytest.mark.asyncio
async def test_posts_exact_official_form_auth_timeout_and_completes() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return _success()

    gateway, client, store = _gateway(handler)
    try:
        result = await gateway.create_call(_request())

        assert result.provider_call_id == CALL_SID
        assert result.status is OutboundCallStatus.QUEUED
        assert result.created_at == NOW
        assert store.complete_count == 1
        request = captured[0]
        assert request.method == "POST"
        assert str(request.url) == _config().create_call_url
        assert request.headers["content-type"].startswith(
            "application/x-www-form-urlencoded"
        )
        authorization = request.headers["authorization"]
        assert authorization.startswith("Basic ")
        assert base64.b64decode(authorization.removeprefix("Basic ")).decode() == (
            f"{API_KEY_SID}:{API_SECRET}"
        )
        assert parse_qsl(request.content.decode()) == [
            ("To", _number("2")),
            ("From", _number("1")),
            ("Url", "https://voice.example.test/twilio/instructions"),
            ("Method", "POST"),
            ("StatusCallback", "https://voice.example.test/twilio/status"),
            ("StatusCallbackMethod", "POST"),
            ("StatusCallbackEvent", "initiated"),
            ("StatusCallbackEvent", "ringing"),
            ("StatusCallbackEvent", "answered"),
            ("StatusCallbackEvent", "completed"),
            ("Record", "false"),
        ]
        assert request.extensions["timeout"] == {
            "connect": 10.0,
            "read": 10.0,
            "write": 10.0,
            "pool": 10.0,
        }
        assert client.is_closed is False
    finally:
        await client.aclose()


@pytest.mark.parametrize(
    "authorized_at",
    [NOW + timedelta(seconds=1), NOW - timedelta(seconds=301)],
)
@pytest.mark.asyncio
async def test_rejects_invalid_authorization_before_store_and_network(
    authorized_at: datetime,
) -> None:
    requests = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return _success()

    gateway, client, store = _gateway(handler)
    request = _request(
        authorization=OutboundCallAuthorization(
            actor_id="operator_01", authorized_at=authorized_at
        )
    )
    try:
        with pytest.raises(OutboundCallAuthorizationError):
            await gateway.create_call(request)
        assert requests == 0
        assert store.reserve_count == 0
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_rejects_unknown_allowlist_label_before_store_and_network() -> None:
    gateway, client, store = _gateway(lambda _: _success())
    try:
        with pytest.raises(OutboundCallAllowlistError):
            await gateway.create_call(_request(destination_label="UNKNOWN"))
        assert store.reserve_count == 0
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_success_replays_and_conflicting_fingerprint_never_dispatches() -> None:
    requests = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return _success()

    gateway, client, _ = _gateway(handler)
    try:
        first = await gateway.create_call(_request())
        replay = await gateway.create_call(_request(correlation_id=CORRELATION_ID))
        assert replay == first
        with pytest.raises(OutboundCallIdempotencyConflict):
            await gateway.create_call(
                _request(call_session_id=UUID("00000000-0000-4000-8000-000000000318"))
            )
        assert requests == 1
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_existing_pending_and_uncertain_never_dispatch() -> None:
    request = _request()
    fingerprint = outbound_call_request_fingerprint(request)
    store = MemoryAttemptStore()
    pending = OutboundCallAttempt(
        operation_id=request.operation_id,
        idempotency_key=request.idempotency_key,
        request_fingerprint=fingerprint,
        state=OutboundCallAttemptState.PENDING,
        result=None,
        uncertainty=None,
        failure=None,
        created_at=NOW,
        updated_at=NOW,
    )
    store.records[request.idempotency_key] = pending
    requests = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return _success()

    gateway, client, _ = _gateway(handler, store=store)
    try:
        with pytest.raises(OutboundCallOutcomeUncertain):
            await gateway.create_call(request)
        await store.mark_uncertain(
            request.idempotency_key,
            fingerprint,
            OutboundCallUncertainState(
                reason=OutboundCallUncertainReason.TIMEOUT,
                occurred_at=NOW,
            ),
        )
        with pytest.raises(OutboundCallOutcomeUncertain):
            await gateway.create_call(request)
        assert requests == 0
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_concurrent_duplicate_elects_only_one_dispatcher() -> None:
    entered = asyncio.Event()
    release = asyncio.Event()
    requests = 0

    async def handler(_: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        entered.set()
        await release.wait()
        return _success()

    gateway, client, _ = _gateway(handler)
    first = asyncio.create_task(gateway.create_call(_request()))
    try:
        await entered.wait()
        with pytest.raises(OutboundCallOutcomeUncertain):
            await gateway.create_call(_request())
        release.set()
        result = await first
        assert result.provider_call_id == CALL_SID
        assert requests == 1
        assert await gateway.create_call(_request()) == result
    finally:
        release.set()
        await client.aclose()


@pytest.mark.parametrize(
    ("status_code", "error_type", "category"),
    [
        (400, OutboundCallProviderError, OutboundCallFailureCategory.INVALID_REQUEST),
        (401, OutboundCallAuthenticationError, OutboundCallFailureCategory.AUTHENTICATION),
        (403, OutboundCallProviderError, OutboundCallFailureCategory.PERMISSION),
        (404, OutboundCallProviderError, OutboundCallFailureCategory.PROVIDER_REJECTED),
    ],
)
@pytest.mark.asyncio
async def test_definitive_provider_failure_is_persisted_and_replayed(
    status_code: int,
    error_type: type[Exception],
    category: OutboundCallFailureCategory,
) -> None:
    requests = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(
            status_code,
            json={"message": API_SECRET, "to": _number("2")},
        )

    gateway, client, store = _gateway(handler)
    try:
        for _ in range(2):
            with pytest.raises(error_type) as caught:
                await gateway.create_call(_request())
            assert API_SECRET not in (repr(caught.value) + str(caught.value))
            assert _number("2") not in (repr(caught.value) + str(caught.value))
        assert requests == 1
        assert store.records["twilio-call-001"].failure is not None
        assert store.records["twilio-call-001"].failure.category is category
    finally:
        await client.aclose()


@pytest.mark.parametrize(
    ("store_operation", "response"),
    [
        ("complete", _success()),
        ("mark_uncertain", httpx.Response(503)),
        ("fail", httpx.Response(400)),
    ],
)
@pytest.mark.asyncio
async def test_terminal_store_failure_after_dispatch_is_safe_and_never_redispatches(
    store_operation: str,
    response: httpx.Response,
) -> None:
    requests = 0
    store = FailingTerminalStore(store_operation)

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return response

    gateway, client, _ = _gateway(handler, store=store)
    try:
        with pytest.raises(OutboundCallOutcomeUncertain) as caught:
            await gateway.create_call(_request())
        rendered = repr(caught.value) + str(caught.value)
        assert "private database" not in rendered
        assert caught.value.__cause__ is None
        assert requests == 1
        assert store.terminal_calls == 1
        assert store.records["twilio-call-001"].state is OutboundCallAttemptState.PENDING

        with pytest.raises(OutboundCallOutcomeUncertain):
            await gateway.create_call(_request())
        assert requests == 1
        assert store.terminal_calls == 1
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_reserve_failure_propagates_before_network() -> None:
    requests = 0

    class ReserveFailureStore(MemoryAttemptStore):
        async def reserve(
            self, attempt: OutboundCallAttempt
        ) -> OutboundCallAttemptReservation:
            del attempt
            raise TerminalStoreFailure("safe persistence unavailable")

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return _success()

    gateway, client, _ = _gateway(handler, store=ReserveFailureStore())
    try:
        with pytest.raises(TerminalStoreFailure, match="safe persistence unavailable"):
            await gateway.create_call(_request())
        assert requests == 0
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_429_retries_with_backoff_then_succeeds() -> None:
    responses = iter([httpx.Response(429), _success()])
    delays: list[float] = []

    async def delay(seconds: float) -> None:
        delays.append(seconds)

    gateway, client, store = _gateway(lambda _: next(responses), delay=delay)
    try:
        result = await gateway.create_call(_request())
        assert result.status is OutboundCallStatus.QUEUED
        assert delays == [0.25]
        assert store.failure_count == 0
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_exhausted_429_is_failed_with_bounded_retry_after() -> None:
    requests = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(429, headers={"Retry-After": "999999"})

    gateway, client, store = _gateway(handler, delay=lambda _: asyncio.sleep(0))
    try:
        with pytest.raises(OutboundCallRateLimitError) as caught:
            await gateway.create_call(_request())
        assert caught.value.retry_after_seconds == 86_400
        assert requests == 2
        assert store.failure_count == 1
    finally:
        await client.aclose()


@pytest.mark.parametrize(
    ("transport_error", "error_type"),
    [
        (httpx.ConnectTimeout("connect timeout"), OutboundCallTimeoutError),
        (httpx.PoolTimeout("pool timeout"), OutboundCallTimeoutError),
        (httpx.ConnectError("connect error"), OutboundCallProviderError),
    ],
)
@pytest.mark.asyncio
async def test_pre_dispatch_transport_failures_retry_boundedly(
    transport_error: httpx.RequestError,
    error_type: type[Exception],
) -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        transport_error.request = request
        raise transport_error

    gateway, client, store = _gateway(handler, delay=lambda _: asyncio.sleep(0))
    try:
        with pytest.raises(error_type):
            await gateway.create_call(_request())
        assert requests == 2
        assert store.failure_count == 1
        assert store.uncertain_count == 0
        with pytest.raises(error_type):
            await gateway.create_call(_request())
        assert requests == 2
    finally:
        await client.aclose()


@pytest.mark.parametrize(
    "transport_error",
    [
        httpx.ConnectTimeout("connect timeout"),
        httpx.PoolTimeout("pool timeout"),
        httpx.ConnectError("connect error"),
    ],
)
@pytest.mark.asyncio
async def test_pre_dispatch_transport_failure_can_succeed_on_bounded_retry(
    transport_error: httpx.RequestError,
) -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        if requests == 1:
            transport_error.request = request
            raise transport_error
        return _success()

    gateway, client, store = _gateway(handler, delay=lambda _: asyncio.sleep(0))
    try:
        assert (await gateway.create_call(_request())).provider_call_id == CALL_SID
        assert requests == 2
        assert store.complete_count == 1
        assert store.uncertain_count == 0
    finally:
        await client.aclose()


@pytest.mark.parametrize(
    "transport_error",
    [httpx.ReadTimeout("read timeout"), httpx.WriteTimeout("write timeout")],
)
@pytest.mark.asyncio
async def test_post_dispatch_timeout_is_uncertain_without_retry(
    transport_error: httpx.TimeoutException,
) -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        transport_error.request = request
        raise transport_error

    gateway, client, store = _gateway(handler)
    try:
        with pytest.raises(OutboundCallOutcomeUncertain):
            await gateway.create_call(_request())
        assert requests == 1
        assert store.uncertain_count == 1
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_post_dispatch_connection_loss_is_uncertain_without_retry() -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        raise httpx.ReadError("private response detail", request=request)

    gateway, client, store = _gateway(handler)
    try:
        with pytest.raises(OutboundCallOutcomeUncertain) as caught:
            await gateway.create_call(_request())
        assert requests == 1
        assert store.uncertain_count == 1
        assert "private response detail" not in (repr(caught.value) + str(caught.value))
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_5xx_is_uncertain_without_retry() -> None:
    requests = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(503, json={"message": API_SECRET})

    gateway, client, store = _gateway(handler)
    try:
        with pytest.raises(OutboundCallOutcomeUncertain):
            await gateway.create_call(_request())
        assert requests == 1
        assert store.uncertain_count == 1
    finally:
        await client.aclose()


class TrackingStream(httpx.AsyncByteStream):
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks
        self.closed = False

    async def __aiter__(self):  # type: ignore[no-untyped-def]
        for chunk in self.chunks:
            yield chunk

    async def aclose(self) -> None:
        self.closed = True


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(201, json={}),
        httpx.Response(201, json={"sid": "CAwrong", "status": "queued"}),
        httpx.Response(201, json={"sid": CALL_SID, "status": "unknown"}),
        httpx.Response(201, content=b"not-json"),
        httpx.Response(204),
    ],
)
@pytest.mark.asyncio
async def test_invalid_success_is_marked_uncertain(
    response: httpx.Response,
) -> None:
    gateway, client, store = _gateway(lambda _: response)
    try:
        with pytest.raises(OutboundCallOutcomeUncertain):
            await gateway.create_call(_request())
        assert store.uncertain_count == 1
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_oversized_response_is_bounded_and_stream_is_closed() -> None:
    stream = TrackingStream([b"x" * 40_000, b"y" * 30_000])
    gateway, client, store = _gateway(lambda _: httpx.Response(201, stream=stream))
    try:
        with pytest.raises(OutboundCallOutcomeUncertain):
            await gateway.create_call(_request())
        assert store.uncertain_count == 1
        assert stream.closed is True
    finally:
        await client.aclose()


@pytest.mark.parametrize(
    ("provider_status", "expected"),
    [
        ("queued", OutboundCallStatus.QUEUED),
        ("initiated", OutboundCallStatus.INITIATED),
        ("ringing", OutboundCallStatus.RINGING),
        ("in-progress", OutboundCallStatus.IN_PROGRESS),
        ("completed", OutboundCallStatus.COMPLETED),
        ("busy", OutboundCallStatus.BUSY),
        ("failed", OutboundCallStatus.FAILED),
        ("no-answer", OutboundCallStatus.NO_ANSWER),
        ("canceled", OutboundCallStatus.CANCELED),
    ],
)
def test_maps_documented_twilio_statuses(
    provider_status: str, expected: OutboundCallStatus
) -> None:
    assert map_twilio_call_status(provider_status) is expected


def test_unknown_twilio_status_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown"):
        map_twilio_call_status("future-provider-status")
