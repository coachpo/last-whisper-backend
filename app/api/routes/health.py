"""Health check endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter

from app.core.config import settings
from app.models.schemas import HealthResponse

router = APIRouter()


@router.get(
    "/",
    response_model=HealthResponse,
    summary="Health check",
    description="Get the health status of the API service",
)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service=settings.app_name,
        version=settings.app_version,
        timestamp=datetime.now(UTC),
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Detailed health check",
    description="Get detailed health status of the API service",
)
async def detailed_health_check():
    """Detailed health check endpoint."""
    return HealthResponse(
        status="healthy",
        service=settings.app_name,
        version=settings.app_version,
        timestamp=datetime.now(UTC),
    )
