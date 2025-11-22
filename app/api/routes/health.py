"""Health check endpoints."""

from datetime import datetime, timezone
from typing import Callable, Optional, Union

from fastapi import APIRouter, Depends

from app.api.dependencies import (
    get_database_manager,
    get_tts_engine,
    get_tts_engine_manager,
)
from app.core.config import settings
from app.models.database_manager import DatabaseManager
from app.models.schemas import HealthCheckResponse
from app.tts_engine.tts_engine_manager import TTSEngineManager
from app.tts_engine.tts_engine_wrapper import TTSEngineWrapper

router = APIRouter()


HealthEvaluator = Callable[[], Union[bool, tuple[bool, Optional[str]]]]


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health check with details",
    description="Get the health status with detailed checks for all services",
)
async def health_check(
    db_manager: DatabaseManager = Depends(get_database_manager),
    tts_service: TTSEngineWrapper = Depends(get_tts_engine),
    task_mgr: TTSEngineManager = Depends(get_tts_engine_manager),
):
    """Health check endpoint with detailed checks."""

    checks: dict = {}
    overall_status = "healthy"

    def add_check(name: str, evaluator: HealthEvaluator) -> None:
        nonlocal overall_status
        try:
            result = evaluator()
            detail: Optional[str] = None
            if isinstance(result, tuple):
                healthy, detail = result
            else:
                healthy = result
            status = "healthy" if healthy else "unhealthy"
        except Exception as exc:  # pragma: no cover - defensive logging
            status = "error"
            detail = str(exc)

        if status != "healthy":
            overall_status = "unhealthy"

        entry = {"status": status}
        if detail:
            entry["detail"] = detail
        checks[name] = entry

    add_check("database", lambda: db_manager.health_check())
    add_check("audio_directory", lambda: db_manager.check_audio_directory())
    add_check(
        "tts_service",
        lambda: (
            tts_service.is_initialized,
            None if tts_service.is_initialized else "not initialized",
        ),
    )
    add_check(
        "task_manager",
        lambda: (
            task_mgr.is_initialized,
            None if task_mgr.is_initialized else "not initialized",
        ),
    )

    checks["service_info"] = {
        "status": "informational",
        "name": settings.app_name,
        "version": settings.app_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    return HealthCheckResponse(
        status=overall_status,
        checks=checks,
    )
