"""Tests for FastAPI exception and health handlers."""

from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_database_manager,
    get_tts_engine,
    get_tts_engine_manager,
)
from app.core.config import settings
from app.main import app


router = APIRouter()


@router.get("/test-error")
def trigger_error():
    raise RuntimeError("boom!")


# Ensure the helper route is registered once
if not any(route.path == "/test-error" for route in app.routes):  # pragma: no branch
    app.include_router(router)


def test_general_exception_handler_includes_detail_in_dev(test_client):
    response = test_client.get("/test-error")

    assert response.status_code == 500
    assert response.json()["detail"] == "boom!"
    assert response.json()["error"] == "Internal server error"


def test_general_exception_handler_hides_detail_in_production(test_client):
    prev_dev = settings.is_development
    prev_prod = settings.is_production
    try:
        settings.is_development = False
        settings.is_production = True

        response = test_client.get("/test-error")

        assert response.status_code == 500
        assert response.json()["detail"] is None
    finally:
        settings.is_development = prev_dev
        settings.is_production = prev_prod


def test_health_endpoint_reports_individual_checks():
    class HealthyDB:
        def health_check(self):
            return True

        def check_audio_directory(self):
            return True

    class HealthyTTS:
        def __init__(self):
            self.is_initialized = True

        def initialize(self):  # pragma: no cover - lifecycle stub
            self.is_initialized = True

        def shutdown(self):  # pragma: no cover - lifecycle stub
            self.is_initialized = False

    class HealthyManager:
        def __init__(self):
            self.is_initialized = True

        def start_monitoring(self):  # pragma: no cover - lifecycle stub
            self.is_initialized = True

        def stop_monitoring(self):  # pragma: no cover - lifecycle stub
            self.is_initialized = False

    overrides = {
        get_database_manager: lambda: HealthyDB(),
        get_tts_engine: lambda: HealthyTTS(),
        get_tts_engine_manager: lambda: HealthyManager(),
    }

    app.dependency_overrides.update(overrides)

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/health")
            payload = response.json()
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert payload["status"] == "healthy"
    for key in ("database", "audio_directory", "tts_service", "task_manager"):
        assert payload["checks"][key]["status"] == "healthy"
    assert payload["checks"]["service_info"]["status"] == "informational"
