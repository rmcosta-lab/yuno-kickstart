from decimal import Decimal

from yuno_backend.payments import (
    CheckoutSessionRequest,
    CustomerRequest,
    MockPaymentGateway,
    Money,
    PaymentGateway,
    PaymentRequest,
    PaymentStatus,
    RefundRequest,
)


async def test_mock_gateway_supports_a_complete_payment_and_refund_flow() -> None:
    gateway = MockPaymentGateway()
    assert isinstance(gateway, PaymentGateway)

    customer = await gateway.create_customer(CustomerRequest(merchant_customer_id="customer-1"))
    amount = Money(currency="BRL", value=Decimal("125.50"))
    checkout = await gateway.create_checkout_session(
        CheckoutSessionRequest(
            customer_id=customer.id,
            merchant_order_id="order-1",
            amount=amount,
            callback_url="https://example.test/callback",
        )
    )
    payment_request = PaymentRequest(
        checkout_session_id=checkout.id,
        one_time_token="one-time-token",
    )
    payment = await gateway.create_payment(payment_request)

    assert payment.amount == amount
    assert payment.status is PaymentStatus.SUCCEEDED
    assert "one-time-token" not in repr(payment_request)

    refund = await gateway.refund_payment(RefundRequest(payment_id=payment.id))

    assert refund.amount == amount
    assert (await gateway.retrieve_payment(payment.id)).status is PaymentStatus.REFUNDED


async def test_mock_customer_creation_is_idempotent_by_merchant_id() -> None:
    gateway = MockPaymentGateway()
    request = CustomerRequest(merchant_customer_id="customer-1")

    assert await gateway.create_customer(request) == await gateway.create_customer(request)
