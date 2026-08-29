"""Shared transport vocabulary for the Volta browser contract."""

from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict, Field, field_validator

PositiveVersion = Annotated[int, Field(ge=1)]
MinorAmount = Annotated[int, Field(ge=0)]
NonNegativeMilliseconds = Annotated[int, Field(ge=0)]
ShortText = Annotated[str, Field(min_length=1, max_length=500)]
LongText = Annotated[str, Field(min_length=1, max_length=10_000)]
SafeIdentifier = Annotated[str, Field(min_length=1, max_length=255)]
OpaqueCursor = Annotated[str, Field(min_length=1, max_length=512)]
CurrencyCode = Literal["MXN"]


class StrictRequestModel(BaseModel):
    """Forbid accidental or server-owned fields in public request bodies."""

    model_config = ConfigDict(extra="forbid")


class ResponseModel(BaseModel):
    """Keep public response serialization explicit and closed."""

    model_config = ConfigDict(extra="forbid")


class RequestedLanguage(StrEnum):
    ES_MX = "ES_MX"
    EN_US = "EN_US"


class BrowserChannel(StrEnum):
    BROWSER_TEXT = "BROWSER_TEXT"
    BROWSER_VOICE = "BROWSER_VOICE"


class SimulatedDirection(StrEnum):
    OUTBOUND_SIMULATION = "OUTBOUND_SIMULATION"
    INBOUND_SIMULATION = "INBOUND_SIMULATION"


class OperationStatus(StrEnum):
    READY = "READY"
    NEGOTIATING = "NEGOTIATING"
    COMMITTED = "COMMITTED"
    ESCALATED = "ESCALATED"
    COMPLETED = "COMPLETED"


class CallState(StrEnum):
    SELECTED = "SELECTED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class QuoteEligibility(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    REJECTED = "REJECTED"


class EvidenceLifecycle(StrEnum):
    CANDIDATE = "CANDIDATE"
    SIMULATED = "SIMULATED"
    VERIFIED = "VERIFIED"


class CommitmentDisposition(StrEnum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"


class RecoveryScenario(StrEnum):
    MANDATE_SAFE = "MANDATE_SAFE"
    OUT_OF_MANDATE = "OUT_OF_MANDATE"


class ResolutionState(StrEnum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


class ActorKind(StrEnum):
    COORDINATOR = "COORDINATOR"
    SYSTEM = "SYSTEM"
    CARRIER_SIMULATOR = "CARRIER_SIMULATOR"


class RouteDetails(ResponseModel):
    origin: ShortText
    destination: ShortText


class PickupWindow(ResponseModel):
    start_date: date
    end_date: date

    @field_validator("end_date")
    @classmethod
    def end_must_not_precede_start(cls, value: date, info: object) -> date:
        data = getattr(info, "data", {})
        start_date = data.get("start_date")
        if start_date is not None and value < start_date:
            raise ValueError("end_date must be on or after start_date")
        return value


class MoneyTerms(ResponseModel):
    amount_minor: MinorAmount
    currency: CurrencyCode
    pickup_window: PickupWindow
    conditions: list[ShortText] = Field(default_factory=list, max_length=25)


def require_utc(value: datetime) -> datetime:
    if value.utcoffset() != timedelta(0):
        raise ValueError("timestamps must use UTC")
    return value


UtcTimestamp = Annotated[AwareDatetime, AfterValidator(require_utc)]


class IdReference(ResponseModel):
    id: UUID
