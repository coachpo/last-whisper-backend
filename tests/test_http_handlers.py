"""Tests for FastAPI exception and health handlers."""

from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.api import dependencies as dependency_cache
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

    prev_db = dependency_cache._database_manager
    prev_tts = dependency_cache._tts_engine
    prev_mgr = dependency_cache._task_manager

    dependency_cache._database_manager = HealthyDB()
    dependency_cache._tts_engine = HealthyTTS()
    dependency_cache._task_manager = HealthyManager()

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/health")
            payload = response.json()
    finally:
        dependency_cache._database_manager = prev_db
        dependency_cache._tts_engine = prev_tts
        dependency_cache._task_manager = prev_mgr

    assert response.status_code == 200
    assert payload["status"] == "healthy"
    assert payload["checks"]["database"] == "healthy"
    assert payload["checks"]["audio_directory"] == "healthy"
    assert payload["checks"]["tts_service"] == "healthy"
    assert payload["checks"]["task_manager"] == "healthy"
