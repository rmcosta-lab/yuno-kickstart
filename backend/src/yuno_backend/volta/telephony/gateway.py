"""Provider-neutral outbound telephony gateway."""

from typing import Protocol, runtime_checkable

from yuno_backend.volta.telephony.models import (
    HumanHandoff,
    OutboundCall,
    OutboundCallRequest,
)

__all__ = ["HumanHandoffGateway", "OutboundCallGateway"]


@runtime_checkable
class HumanHandoffGateway(Protocol):
    async def begin_handoff(self, handoff: HumanHandoff) -> None: ...


@runtime_checkable
class OutboundCallGateway(Protocol):
    async def create_call(self, request: OutboundCallRequest) -> OutboundCall: ...
