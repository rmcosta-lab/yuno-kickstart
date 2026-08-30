"""FastAPI application factory."""

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from time import monotonic

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.contract_service import ContractServiceError
from app.errors import (
    contract_service_error_handler,
    validation_error_handler,
)
from app.logging import configure_logging
from app.middleware.rate_limit import MutationRateLimitMiddleware, SlidingWindowRateLimiter
from app.middleware.realtime_cache import RealtimeNoStoreMiddleware
from app.middleware.request_context import RequestContextMiddleware
from app.middleware.unexpected_errors import UnexpectedErrorMiddleware
from app.openai_client import configure_openai_http_client, get_openai_http_client
from app.routers.contracts import router as contracts_router
from app.routers.health import router as health_router
from app.routers.realtime import router as realtime_router
from app.routers.telephony import router as telephony_router


@asynccontextmanager
async def application_lifespan(application: FastAPI) -> AsyncIterator[None]:
    get_openai_http_client(application)
    try:
        yield
    finally:
        try:
            telephony = getattr(application.state, "telephony_application", None)
            telephony_close = getattr(telephony, "aclose", None)
            if telephony_close is not None:
                await telephony_close()
        finally:
            try:
                service = getattr(application.state, "contract_service", None)
                close = getattr(service, "aclose", None)
                if close is not None:
                    await close()
            finally:
                client = getattr(application.state, "openai_http_client", None)
                if client is not None:
                    await client.aclose()


def create_app(
    settings: Settings | None = None,
    *,
    mutation_rate_limit_clock: Callable[[], float] = monotonic,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings)

    application = FastAPI(
        title=resolved_settings.api_title,
        version=resolved_settings.api_version,
        description="Thin HTTP contract boundary for the Volta hackathon demo.",
        lifespan=application_lifespan,
    )
    application.state.settings = resolved_settings
    application.state.twilio_media_lock = asyncio.Lock()
    application.state.twilio_media_active = False
    configure_openai_http_client(application)
    mutation_rate_limiter = SlidingWindowRateLimiter(
        request_limit=resolved_settings.volta_mutation_rate_limit_requests,
        window_seconds=resolved_settings.volta_mutation_rate_limit_window_seconds,
        max_identities=resolved_settings.volta_mutation_rate_limit_max_identities,
        clock=mutation_rate_limit_clock,
    )
    application.state.mutation_rate_limiter = mutation_rate_limiter
    application.add_exception_handler(ContractServiceError, contract_service_error_handler)
    application.add_exception_handler(RequestValidationError, validation_error_handler)
    application.add_middleware(UnexpectedErrorMiddleware)
    application.add_middleware(
        MutationRateLimitMiddleware,
        settings=resolved_settings,
        limiter=mutation_rate_limiter,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
        expose_headers=[
            "X-Request-ID",
            "Idempotency-Replayed",
            "Cache-Control",
            "Pragma",
            "Retry-After",
        ],
    )
    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(RealtimeNoStoreMiddleware)
    application.include_router(health_router)
    application.include_router(contracts_router)
    application.include_router(realtime_router)
    application.include_router(telephony_router)
    return application


app = create_app()
