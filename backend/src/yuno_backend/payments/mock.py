"""In-memory payment gateway for deterministic local development and tests."""

from dataclasses import replace

from yuno_backend.payments.models import (
    CheckoutSession,
    CheckoutSessionRequest,
    Customer,
    CustomerRequest,
    Payment,
    PaymentNotFoundError,
    PaymentRequest,
    PaymentStatus,
    Refund,
    RefundRequest,
)


class MockPaymentGateway:
    def __init__(self) -> None:
        self._sequence = 0
        self.customers: dict[str, Customer] = {}
        self.checkout_sessions: dict[str, CheckoutSession] = {}
        self.payments: dict[str, Payment] = {}
        self.refunds: dict[str, Refund] = {}

    def _next_id(self, kind: str) -> str:
        self._sequence += 1
        return f"mock-{kind}-{self._sequence}"

    async def create_customer(self, request: CustomerRequest) -> Customer:
        existing = self.customers.get(request.merchant_customer_id)
        if existing is not None:
            return existing

        customer = Customer(
            id=self._next_id("customer"),
            merchant_customer_id=request.merchant_customer_id,
        )
        self.customers[request.merchant_customer_id] = customer
        return customer

    async def create_checkout_session(
        self,
        request: CheckoutSessionRequest,
    ) -> CheckoutSession:
        checkout_session = CheckoutSession(
            id=self._next_id("checkout"),
            customer_id=request.customer_id,
            merchant_order_id=request.merchant_order_id,
            amount=request.amount,
        )
        self.checkout_sessions[checkout_session.id] = checkout_session
        return checkout_session

    async def create_payment(self, request: PaymentRequest) -> Payment:
        try:
            checkout_session = self.checkout_sessions[request.checkout_session_id]
        except KeyError as error:
            message = f"Checkout session {request.checkout_session_id!r} was not found"
            raise PaymentNotFoundError(message) from error

        payment = Payment(
            id=self._next_id("payment"),
            checkout_session_id=checkout_session.id,
            amount=checkout_session.amount,
            status=PaymentStatus.SUCCEEDED,
            provider_status="mock_succeeded",
        )
        self.payments[payment.id] = payment
        return payment

    async def retrieve_payment(self, payment_id: str) -> Payment:
        try:
            return self.payments[payment_id]
        except KeyError as error:
            message = f"Payment {payment_id!r} was not found"
            raise PaymentNotFoundError(message) from error

    async def refund_payment(self, request: RefundRequest) -> Refund:
        payment = await self.retrieve_payment(request.payment_id)
        refund = Refund(
            id=self._next_id("refund"),
            payment_id=payment.id,
            amount=request.amount or payment.amount,
            status=PaymentStatus.SUCCEEDED,
        )
        self.refunds[refund.id] = refund
        self.payments[payment.id] = replace(
            payment,
            status=PaymentStatus.REFUNDED,
            provider_status="mock_refunded",
        )
        return refund
