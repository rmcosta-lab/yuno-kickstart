"""Application-facing payment provider boundary."""

from typing import Protocol, runtime_checkable

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


@runtime_checkable
class PaymentGateway(Protocol):
    async def create_customer(self, request: CustomerRequest) -> Customer: ...

    async def create_checkout_session(
        self,
        request: CheckoutSessionRequest,
    ) -> CheckoutSession: ...

    async def create_payment(self, request: PaymentRequest) -> Payment: ...

    async def retrieve_payment(self, payment_id: str) -> Payment: ...

    async def refund_payment(self, request: RefundRequest) -> Refund: ...
