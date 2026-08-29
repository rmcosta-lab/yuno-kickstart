"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.contract_service import ContractServiceError
from app.errors import (
    contract_service_error_handler,
    unexpected_error_handler,
    validation_error_handler,
)
from app.logging import configure_logging
from app.middleware.request_context import RequestContextMiddleware
from app.routers.contracts import router as contracts_router
from app.routers.health import router as health_router


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings)

    application = FastAPI(
        title=resolved_settings.api_title,
        version=resolved_settings.api_version,
        description="Thin HTTP contract boundary for the Volta hackathon demo.",
    )
    application.state.settings = resolved_settings
    application.add_exception_handler(ContractServiceError, contract_service_error_handler)
    application.add_exception_handler(RequestValidationError, validation_error_handler)
    application.add_exception_handler(Exception, unexpected_error_handler)
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
