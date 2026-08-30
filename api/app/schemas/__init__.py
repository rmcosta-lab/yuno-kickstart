"""Public Pydantic HTTP contracts."""
from app.schemas.telephony import CreateOutboundCallRequest, OutboundCallResponse

__all__ = ["CreateOutboundCallRequest", "OutboundCallResponse"]
