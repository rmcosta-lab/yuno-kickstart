from decimal import Decimal

import httpx
import pytest
from yuno_backend.integrations.yuno import (
    YUNO_SANDBOX_BASE_URL,
    YunoConfig,
    YunoIntegrationNotImplementedError,
    YunoPaymentGateway,
)
from yuno_backend.payments import Money, PaymentGateway, PaymentRequest


def test_yuno_config_defaults_to_sandbox_and_redacts_keys() -> None:
    config = YunoConfig(public_api_key="public", private_secret_key="private")

    assert config.base_url == YUNO_SANDBOX_BASE_URL
    assert config.request_headers() == {
        "public-api-key": "public",
        "private-secret-key": "private",
    }
    assert "public" not in repr(config)
    assert "private" not in repr(config)


async def test_yuno_skeleton_never_makes_an_unverified_network_call() -> None:
    request_count = 0

    async def fail_if_called(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(500, request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(fail_if_called))
    gateway = YunoPaymentGateway(
        YunoConfig(public_api_key="public", private_secret_key="private"),
        client=client,
    )
    assert isinstance(gateway, PaymentGateway)

    with pytest.raises(YunoIntegrationNotImplementedError, match="official endpoint schema"):
        await gateway.create_payment(
            PaymentRequest(checkout_session_id="checkout-1", one_time_token="token")
        )

    assert request_count == 0
    await client.aclose()


def test_money_uses_decimal_values() -> None:
    amount = Money(currency="BRL", value=Decimal("10.01"))

    assert amount.value == Decimal("10.01")
