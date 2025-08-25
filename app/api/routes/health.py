"""Health check endpoints."""

import os
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.core.config import settings
from app.models.database import DatabaseManager
from app.models.schemas import HealthResponse, HealthCheckResponse

router = APIRouter()


def get_database_manager() -> DatabaseManager:
    """Get database manager instance."""
    # This will be implemented in dependencies.py
    from app.api.dependencies import get_database_manager as _get_database_manager
    return _get_database_manager()


@router.get(
    "/healthz",
    response_model=HealthCheckResponse,
    summary="Health check with details",
    description="Get the health status with detailed checks",
)
async def health_check(
        db_manager: DatabaseManager = Depends(get_database_manager),
):
    """Health check endpoint with detailed checks."""
    checks = {}
    overall_status = "healthy"

    # Check database connectivity
    try:
        db_healthy = db_manager.health_check()
        checks["database"] = "healthy" if db_healthy else "unhealthy"
        if not db_healthy:
            overall_status = "unhealthy"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"
        overall_status = "unhealthy"

    # Check audio directory
    try:
        audio_writable = db_manager.check_audio_directory()
        checks["audio_directory"] = "healthy" if audio_writable else "unhealthy"
        if not audio_writable:
            overall_status = "unhealthy"
    except Exception as e:
        checks["audio_directory"] = f"error: {str(e)}"
        overall_status = "unhealthy"

    # Check TTS worker (if available)
    try:
        from app.services.outer.tts_service import tts_service
        checks["tts_service"] = "healthy" if tts_service.is_initialized else "not_initialized"

        # Also check task manager
        from app.services.task_manager import task_manager
        checks["task_manager"] = "healthy" if task_manager.is_initialized else "not_initialized"
    except Exception as e:
        checks["tts_service"] = f"error: {str(e)}"
        checks["task_manager"] = f"error: {str(e)}"

    return HealthCheckResponse(
        status=overall_status,
        checks=checks,
    )


@router.get(
    "/",
    response_model=HealthResponse,
    summary="Basic health check",
    description="Get basic health status of the API service",
)
async def basic_health_check():
    """Basic health check endpoint."""
    return HealthResponse(
        status="healthy",
        service=settings.app_name,
        version=settings.app_version,
        timestamp=datetime.now(UTC),
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Legacy health check",
    description="Legacy health check endpoint",
)
async def legacy_health_check():
    """Legacy health check endpoint."""
    return HealthResponse(
        status="healthy",
        service=settings.app_name,
        version=settings.app_version,
        timestamp=datetime.now(UTC),
    )


# Generic audio serving endpoint
@router.get("/v1/audio/{filename}")
async def serve_audio(filename: str):
    """Serve audio files."""
    # Validate filename for security
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename",
        )

    if not filename.endswith('.wav'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only WAV files are supported",
        )

    audio_path = os.path.join(settings.audio_dir, filename)

    if not os.path.exists(audio_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio file not found",
        )

    return FileResponse(
        path=audio_path,
        media_type="audio/wav",
        filename=filename,
    )
