"""Safe ASGI translation for unexpected HTTP application errors."""

from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.errors import unexpected_error_handler


class UnexpectedErrorMiddleware:
    """Translate route errors before CORS and request-context middleware unwind."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_started = False

        async def send_with_response_state(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, send_with_response_state)
        except Exception as error:
            if response_started:
                raise
            response = await unexpected_error_handler(Request(scope), error)
            await response(scope, receive, send)
