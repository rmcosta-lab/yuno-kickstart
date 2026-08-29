"""Request correlation and metadata-only structured access logging."""

from time import perf_counter
from uuid import uuid4

import structlog
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from structlog.contextvars import bind_contextvars, clear_contextvars

_REQUEST_ID_HEADER = "x-request-id"
_REQUEST_ID_MAX_LENGTH = 128


def _valid_request_id(value: str | None) -> bool:
    return bool(
        value
        and len(value) <= _REQUEST_ID_MAX_LENGTH
        and all(character.isalnum() or character in "-_." for character in value)
    )


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.log = structlog.get_logger("api.access")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming_request_id = Headers(scope=scope).get(_REQUEST_ID_HEADER)
        request_id = incoming_request_id if _valid_request_id(incoming_request_id) else str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        clear_contextvars()
        bind_contextvars(request_id=request_id)

        method = scope.get("method", "")
        path = scope.get("path", "")
        status_code = 500
        started_at = perf_counter()

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message)[_REQUEST_ID_HEADER] = request_id
            await send(message)

        self.log.info("http.request.started", method=method, path=path)
        try:
            await self.app(scope, receive, send_with_request_id)
        except BaseException:
            self.log.error("http.request.failed", method=method, path=path)
            raise
        finally:
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            self.log.info(
                "http.request.completed",
                method=method,
                path=path,
                status_code=status_code,
                duration_ms=duration_ms,
            )
            clear_contextvars()
