"""Provider-neutral outbound telephony gateway."""

from typing import Protocol, runtime_checkable

from yuno_backend.volta.telephony.models import OutboundCall, OutboundCallRequest

__all__ = ["OutboundCallGateway"]


@runtime_checkable
class OutboundCallGateway(Protocol):
    async def create_call(self, request: OutboundCallRequest) -> OutboundCall: ...
