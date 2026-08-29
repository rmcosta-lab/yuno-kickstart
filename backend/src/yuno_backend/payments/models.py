"""Provider-neutral values passed through the payment gateway boundary."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


@dataclass(frozen=True, slots=True)
class Money:
    currency: str
    value: Decimal


@dataclass(frozen=True, slots=True)
class CustomerRequest:
    merchant_customer_id: str


@dataclass(frozen=True, slots=True)
class Customer:
    id: str
    merchant_customer_id: str


@dataclass(frozen=True, slots=True)
class CheckoutSessionRequest:
    customer_id: str
    merchant_order_id: str
    amount: Money
    callback_url: str
    description: str | None = None


@dataclass(frozen=True, slots=True)
class CheckoutSession:
    id: str
    customer_id: str
    merchant_order_id: str
    amount: Money
    expires_at: datetime | None = None


class PaymentStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    REFUNDED = "refunded"


@dataclass(frozen=True, slots=True)
class PaymentRequest:
    checkout_session_id: str
    one_time_token: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class Payment:
    id: str
    checkout_session_id: str
    amount: Money
    status: PaymentStatus
    provider_status: str | None = None


@dataclass(frozen=True, slots=True)
class RefundRequest:
    payment_id: str
    amount: Money | None = None


@dataclass(frozen=True, slots=True)
class Refund:
    id: str
    payment_id: str
    amount: Money
    status: PaymentStatus


class PaymentNotFoundError(LookupError):
    """Raised when a gateway cannot find a requested payment."""
