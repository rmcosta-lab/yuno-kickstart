"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.logging import configure_logging
from app.middleware.request_context import RequestContextMiddleware
from app.routers.health import router as health_router


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings)

    application = FastAPI(
        title=resolved_settings.api_title,
        version=resolved_settings.api_version,
        description="Thin HTTP boundary for the Yuno × Nauta hackathon demo.",
    )
    application.state.settings = resolved_settings
    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Request-ID", "X-HMAC-Signature"],
    )
    application.include_router(health_router)
    return application


app = create_app()
