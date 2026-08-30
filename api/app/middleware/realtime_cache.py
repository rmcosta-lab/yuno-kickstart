"""Prevent storage of the credential route and all of its error responses."""

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REALTIME_CLIENT_SECRET_PATH = "/v1/realtime/client-secrets"
CACHE_CONTROL = "no-store, private, max-age=0"


class RealtimeNoStoreMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") != REALTIME_CLIENT_SECRET_PATH:
            await self.app(scope, receive, send)
            return

        async def send_no_store(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["Cache-Control"] = CACHE_CONTROL
                headers["Pragma"] = "no-cache"
            await send(message)

        await self.app(scope, receive, send_no_store)
