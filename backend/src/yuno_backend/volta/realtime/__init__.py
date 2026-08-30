"""Provider-neutral realtime voice contracts."""

from yuno_backend.volta.realtime.errors import (
    InvalidRealtimeEvent,
    RealtimeAuthenticationError,
    RealtimeConnectionError,
    RealtimeDisconnectedError,
    RealtimeError,
    RealtimeModelUnavailableError,
    RealtimeProviderError,
    RealtimeRateLimitError,
    RealtimeTimeoutError,
)
from yuno_backend.volta.realtime.gateway import RealtimeConnection, RealtimeGateway
from yuno_backend.volta.realtime.models import (
    PcmAudioFormat,
    RealtimeAudioDelta,
    RealtimeEvent,
    RealtimeResponseCancelled,
    RealtimeResponseCompleted,
    RealtimeSessionReady,
    RealtimeSessionRequest,
    RealtimeSpeechStarted,
    RealtimeSpeechStopped,
    RealtimeToolCallRequested,
    RealtimeToolDefinition,
    RealtimeToolOutput,
)

__all__ = [
    "InvalidRealtimeEvent",
    "PcmAudioFormat",
    "RealtimeAudioDelta",
    "RealtimeAuthenticationError",
    "RealtimeConnection",
    "RealtimeConnectionError",
    "RealtimeDisconnectedError",
    "RealtimeError",
    "RealtimeEvent",
    "RealtimeGateway",
    "RealtimeModelUnavailableError",
    "RealtimeProviderError",
    "RealtimeRateLimitError",
    "RealtimeResponseCancelled",
    "RealtimeResponseCompleted",
    "RealtimeSessionReady",
    "RealtimeSessionRequest",
    "RealtimeSpeechStarted",
    "RealtimeSpeechStopped",
    "RealtimeTimeoutError",
    "RealtimeToolCallRequested",
    "RealtimeToolDefinition",
    "RealtimeToolOutput",
]
