from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import httpx
import pytest
from yuno_backend.integrations.twilio import (
    InMemoryTwilioHandoffBindingStore,
    TwilioDestinationAllowlist,
    TwilioHandoffStatusCallback,
    TwilioHumanHandoffConfig,
    TwilioHumanHandoffGateway,
)
from yuno_backend.volta.telephony import (
    HumanHandoff,
    HumanHandoffAuthenticationError,
    HumanHandoffContext,
    HumanHandoffDestinationError,
    HumanHandoffOutcomeUncertain,
    HumanHandoffPermissionError,
    HumanHandoffProviderError,
    HumanHandoffRateLimitError,
    HumanHandoffStatus,
    HumanHandoffTimeoutError,
)

NOW = datetime(2026, 8, 30, 15, tzinfo=UTC)
CALL_ID = UUID("10000000-0000-0000-0000-000000000001")
HANDOFF_ID = UUID("20000000-0000-0000-0000-000000000001")
REMOTE_SID = "CA" + "1" * 32
COORDINATOR_SID = "CA" + "2" * 32
CONFERENCE_SID = "CF" + "3" * 32
ACCOUNT_SID = "AC" + "4" * 32


class Resolver:
    async def provider_call_sid(self, call_id: UUID) -> str | None:
        return REMOTE_SID if call_id == CALL_ID else None


def config() -> TwilioHumanHandoffConfig:
    return TwilioHumanHandoffConfig(
        account_sid=ACCOUNT_SID,
        api_key_sid="SK" + "5" * 32,
        api_key_secret="synthetic-secret",
        coordinator_caller_id_e164="+15555550101",
        status_callback_url="https://demo.example.com/v1/telephony/twilio/handoff-status",
    )


def handoff() -> HumanHandoff:
    return HumanHandoff(
        handoff_id=HANDOFF_ID,
        call_id=CALL_ID,
        coordinator_destination_label="coordinator-demo",
        idempotency_key="handoff-key-0001",
        request_fingerprint="f" * 64,
        status=HumanHandoffStatus.CONNECTING,
        requested_at=NOW,
        status_updated_at=NOW,
        context=HumanHandoffContext(1, (), (), (), "IN_PROGRESS"),
    )


def gateway(
    client: httpx.AsyncClient,
    *,
    resolver: object | None = None,
    allowlist: TwilioDestinationAllowlist | None = None,
) -> TwilioHumanHandoffGateway:
    return TwilioHumanHandoffGateway(
        client,
        config(),
        allowlist or TwilioDestinationAllowlist({"coordinator-demo": "+15555550102"}),
        resolver or Resolver(),
        InMemoryTwilioHandoffBindingStore(),
    )


async def test_adapter_updates_live_call_then_adds_only_allowlisted_coordinator() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("Participants.json"):
            return httpx.Response(
                201,
                json={"call_sid": COORDINATOR_SID, "conference_sid": CONFERENCE_SID},
            )
        return httpx.Response(200, json={"sid": REMOTE_SID})

    store = InMemoryTwilioHandoffBindingStore()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        gateway = TwilioHumanHandoffGateway(
            client,
            config(),
            TwilioDestinationAllowlist({"coordinator-demo": "+15555550102"}),
            Resolver(),
            store,
        )
        await gateway.begin_handoff(handoff())
        await gateway.begin_handoff(handoff())

    assert len(requests) == 2
    assert f"/Calls/{REMOTE_SID}.json" in requests[0].url.path
    assert b"volta-handoff-20000000000000000000000000000001" in requests[0].content
    assert b"%2B15555550102" in requests[1].content


async def test_callbacks_accumulate_presence_and_reject_out_of_order_resurrection() -> None:
    store = InMemoryTwilioHandoffBindingStore()
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: None)) as client:
        gateway = TwilioHumanHandoffGateway(
            client,
            config(),
            TwilioDestinationAllowlist({"coordinator-demo": "+15555550102"}),
            Resolver(),
            store,
        )
        await store.reserve(
            __import__("yuno_backend.integrations.twilio.handoff", fromlist=["_Binding"])._Binding(
                HANDOFF_ID, CALL_ID, REMOTE_SID, "conference-demo"
            )
        )
        await store.attach_coordinator(HANDOFF_ID, CONFERENCE_SID, COORDINATOR_SID)

        def callback(event_id: str, sid: str, event: str, sequence: int):
            return TwilioHandoffStatusCallback(
                event_id * 64,
                ACCOUNT_SID,
                sid,
                CONFERENCE_SID,
                event,
                sequence,
                NOW,
            )

        remote = await gateway.map_status_callback(callback("a", REMOTE_SID, "participant-join", 1))
        assert remote.status is HumanHandoffStatus.CONNECTING
        joined = await gateway.map_status_callback(
            callback("b", COORDINATOR_SID, "participant-join", 2)
        )
        assert joined.status is HumanHandoffStatus.JOINED
        left = await gateway.map_status_callback(callback("c", REMOTE_SID, "participant-leave", 4))
        assert left.status is HumanHandoffStatus.FAILED_SAFE
        stale = await gateway.map_status_callback(callback("d", REMOTE_SID, "participant-join", 3))
        assert stale.status is HumanHandoffStatus.CONNECTING
        assert stale.remote_participant_present is False
        assert stale.coordinator_participant_present is True


async def test_duplicate_remote_join_retry_after_binding_only_commit_stays_connecting() -> None:
    store = InMemoryTwilioHandoffBindingStore()
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: None)) as client:
        adapter = TwilioHumanHandoffGateway(
            client,
            config(),
            TwilioDestinationAllowlist({"coordinator-demo": "+15555550102"}),
            Resolver(),
            store,
        )
        await store.reserve(
            __import__("yuno_backend.integrations.twilio.handoff", fromlist=["_Binding"])._Binding(
                HANDOFF_ID, CALL_ID, REMOTE_SID, "conference-demo"
            )
        )
        await store.attach_coordinator(HANDOFF_ID, CONFERENCE_SID, COORDINATOR_SID)
        callback = TwilioHandoffStatusCallback(
            "e" * 64,
            ACCOUNT_SID,
            REMOTE_SID,
            CONFERENCE_SID,
            "participant-join",
            1,
            NOW,
        )

        binding_only_commit = await adapter.map_status_callback(callback)
        retry = await adapter.map_status_callback(callback)

    assert binding_only_commit.status is HumanHandoffStatus.CONNECTING
    assert retry.status is HumanHandoffStatus.CONNECTING
    assert retry.provider_event_id == binding_only_commit.provider_event_id
    assert retry.remote_participant_present is True
    assert retry.coordinator_participant_present is False


async def test_remote_join_can_bind_conference_before_participant_response() -> None:
    store = InMemoryTwilioHandoffBindingStore()
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: None)) as client:
        adapter = TwilioHumanHandoffGateway(
            client,
            config(),
            TwilioDestinationAllowlist({"coordinator-demo": "+15555550102"}),
            Resolver(),
            store,
        )
        await store.reserve(
            __import__("yuno_backend.integrations.twilio.handoff", fromlist=["_Binding"])._Binding(
                HANDOFF_ID, CALL_ID, REMOTE_SID, "conference-demo"
            )
        )
        remote = await adapter.map_status_callback(
            TwilioHandoffStatusCallback(
                "1" * 64,
                ACCOUNT_SID,
                REMOTE_SID,
                CONFERENCE_SID,
                "participant-join",
                1,
                NOW,
            )
        )
        await store.attach_coordinator(HANDOFF_ID, CONFERENCE_SID, COORDINATOR_SID)
        joined = await adapter.map_status_callback(
            TwilioHandoffStatusCallback(
                "2" * 64,
                ACCOUNT_SID,
                COORDINATOR_SID,
                CONFERENCE_SID,
                "participant-join",
                2,
                NOW,
            )
        )

    assert remote.status is HumanHandoffStatus.CONNECTING
    assert remote.remote_participant_present is True
    assert joined.status is HumanHandoffStatus.JOINED


async def test_callback_bound_conference_cannot_be_replaced() -> None:
    store = InMemoryTwilioHandoffBindingStore()
    await store.reserve(
        __import__("yuno_backend.integrations.twilio.handoff", fromlist=["_Binding"])._Binding(
            HANDOFF_ID, CALL_ID, REMOTE_SID, "conference-demo"
        )
    )
    await store.apply_callback(
        TwilioHandoffStatusCallback(
            "3" * 64,
            ACCOUNT_SID,
            REMOTE_SID,
            CONFERENCE_SID,
            "participant-join",
            1,
            NOW,
        )
    )

    with pytest.raises(HumanHandoffPermissionError):
        await store.attach_coordinator(HANDOFF_ID, "CF" + "9" * 32, COORDINATOR_SID)


@pytest.mark.parametrize(
    ("status_code", "error_type"),
    [
        (401, HumanHandoffAuthenticationError),
        (403, HumanHandoffPermissionError),
        (429, HumanHandoffRateLimitError),
        (400, HumanHandoffProviderError),
        (503, HumanHandoffOutcomeUncertain),
    ],
)
async def test_provider_statuses_translate_to_safe_typed_errors(
    status_code: int, error_type: type[Exception]
) -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(status_code))
    ) as client:
        with pytest.raises(error_type) as captured:
            await gateway(client).begin_handoff(handoff())
    assert "+15555550102" not in repr(captured.value)
    assert REMOTE_SID not in repr(captured.value)


@pytest.mark.parametrize(
    ("transport_error", "error_type"),
    [
        (httpx.ReadTimeout("timed out"), HumanHandoffTimeoutError),
        (httpx.ReadError("connection lost"), HumanHandoffOutcomeUncertain),
    ],
)
async def test_transport_failures_are_safe_and_never_retried(
    transport_error: httpx.RequestError, error_type: type[Exception]
) -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        transport_error.request = request
        raise transport_error

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(error_type):
            await gateway(client).begin_handoff(handoff())
    assert requests == 1


@pytest.mark.parametrize(
    "participant_response",
    [
        httpx.Response(201, content=b"not-json"),
        httpx.Response(201, content=b"{" + b"x" * 65_536 + b"}"),
        httpx.Response(201, json={"call_sid": "invalid", "conference_sid": "invalid"}),
    ],
)
async def test_invalid_or_oversized_participant_response_is_uncertain(
    participant_response: httpx.Response,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("Participants.json"):
            return participant_response
        return httpx.Response(200)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(HumanHandoffOutcomeUncertain):
            await gateway(client).begin_handoff(handoff())


async def test_unknown_destination_and_invalid_call_binding_do_zero_provider_io() -> None:
    requests = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(200)

    class MissingResolver:
        async def provider_call_sid(self, call_id: UUID) -> str | None:
            return None

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        unknown = handoff()
        unknown = __import__("dataclasses").replace(
            unknown, coordinator_destination_label="unknown"
        )
        with pytest.raises(HumanHandoffDestinationError):
            await gateway(client).begin_handoff(unknown)
        with pytest.raises(HumanHandoffProviderError):
            await gateway(client, resolver=MissingResolver()).begin_handoff(handoff())
    assert requests == 0


def test_configuration_callback_and_errors_have_redacted_representations() -> None:
    configuration = config()
    callback = TwilioHandoffStatusCallback(
        "a" * 64,
        ACCOUNT_SID,
        REMOTE_SID,
        CONFERENCE_SID,
        "participant-join",
        1,
        NOW,
    )
    rendered = repr((configuration, callback))
    assert "synthetic-secret" not in rendered
    assert "+15555550101" not in rendered
    assert ACCOUNT_SID not in rendered
    assert REMOTE_SID not in rendered
    assert CONFERENCE_SID not in rendered
    error = HumanHandoffProviderError(call_id=CALL_ID)
    assert error.safe_metadata == {
        "category": "provider",
        "call_id": str(CALL_ID),
    }
