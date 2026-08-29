"""Process health endpoint."""

from fastapi import APIRouter

from app.schemas.health import HealthResponse

router = APIRouter(tags=["system"])


@router.get(
    "/health",
    operation_id="get_health",
    summary="Check API health",
)
def get_health() -> HealthResponse:
    return HealthResponse(status="ok")
