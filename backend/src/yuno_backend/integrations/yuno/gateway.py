"""Yuno gateway seam awaiting an endpoint-specific, docs-verified implementation."""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx

from yuno_backend.payments.models import (
    CheckoutSession,
    CheckoutSessionRequest,
    Customer,
    CustomerRequest,
    Payment,
    PaymentRequest,
    Refund,
    RefundRequest,
)

YUNO_SANDBOX_BASE_URL = "https://api-sandbox.y.uno"


class YunoIntegrationNotImplementedError(NotImplementedError):
    """Raised until a concrete Yuno operation is specified from current docs."""


@dataclass(frozen=True, slots=True)
class YunoConfig:
    public_api_key: str = field(repr=False)
    private_secret_key: str = field(repr=False)
    base_url: str = YUNO_SANDBOX_BASE_URL
    timeout_seconds: float = 60.0
    account_code: str | None = None
    account_id: str | None = None
    country_code: str | None = None
    currency: str | None = None

    def __post_init__(self) -> None:
        if not self.public_api_key or not self.private_secret_key:
            message = "Yuno public and private API keys are required"
            raise ValueError(message)
        if not self.base_url.startswith("https://"):
            message = "Yuno base URL must use HTTPS"
            raise ValueError(message)
        if self.timeout_seconds <= 0:
            message = "Yuno timeout must be positive"
            raise ValueError(message)
        object.__setattr__(self, "base_url", self.base_url.rstrip("/"))

    def request_headers(self) -> dict[str, str]:
        """Return the authentication headers documented by Yuno."""

        return {
            "public-api-key": self.public_api_key,
            "private-secret-key": self.private_secret_key,
        }


class YunoPaymentGateway:
    """A safe adapter shell that cannot issue a payment call accidentally."""

    def __init__(
        self,
        config: YunoConfig,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = config
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> YunoPaymentGateway:
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    def _http_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._config.base_url,
                headers=self._config.request_headers(),
                timeout=httpx.Timeout(self._config.timeout_seconds),
            )
        return self._client

    @staticmethod
    def _not_implemented(operation: str) -> YunoIntegrationNotImplementedError:
        message = (
            f"Yuno {operation} is not implemented: "
            "verify the current official endpoint schema first"
        )
        return YunoIntegrationNotImplementedError(
            message
        )

    async def create_customer(self, request: CustomerRequest) -> Customer:
        del request
        raise self._not_implemented("customer creation")

    async def create_checkout_session(
        self,
        request: CheckoutSessionRequest,
    ) -> CheckoutSession:
        del request
        raise self._not_implemented("checkout-session creation")

    async def create_payment(self, request: PaymentRequest) -> Payment:
        del request
        raise self._not_implemented("payment creation")

    async def retrieve_payment(self, payment_id: str) -> Payment:
        del payment_id
        raise self._not_implemented("payment retrieval")

    async def refund_payment(self, request: RefundRequest) -> Refund:
        del request
        raise self._not_implemented("payment refund")
