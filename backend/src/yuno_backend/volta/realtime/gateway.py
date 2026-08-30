"""Provider-neutral async realtime gateway protocols."""

from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager
from typing import Protocol

from yuno_backend.volta.realtime.models import (
    RealtimeEvent,
    RealtimePlaybackTruncation,
    RealtimeSessionRequest,
    RealtimeToolOutput,
)

__all__ = ["RealtimeConnection", "RealtimeGateway"]


class RealtimeConnection(Protocol):
    async def send_audio(self, chunk: bytes) -> None: ...

    async def truncate_playback(self, truncation: RealtimePlaybackTruncation) -> None: ...

    async def send_tool_output(self, output: RealtimeToolOutput) -> None: ...

    def events(self) -> AsyncIterator[RealtimeEvent]: ...

    async def close(self) -> None: ...


class RealtimeGateway(Protocol):
    def connect(
        self, request: RealtimeSessionRequest
    ) -> AbstractAsyncContextManager[RealtimeConnection]: ...
