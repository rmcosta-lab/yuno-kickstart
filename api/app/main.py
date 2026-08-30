"""FastAPI application factory."""

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
from app.middleware.request_context import RequestContextMiddleware
from app.middleware.unexpected_errors import UnexpectedErrorMiddleware
from app.routers.contracts import router as contracts_router
from app.routers.health import router as health_router


@asynccontextmanager
async def application_lifespan(application: FastAPI) -> AsyncIterator[None]:
    try:
        yield
    finally:
        service = getattr(application.state, "contract_service", None)
        close = getattr(service, "aclose", None)
        if close is not None:
            await close()


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
        expose_headers=["X-Request-ID", "Idempotency-Replayed"],
    )
    application.add_middleware(RequestContextMiddleware)
    application.include_router(health_router)
    application.include_router(contracts_router)
    return application


app = create_app()
