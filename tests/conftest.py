"""Shared pytest fixtures for the last-whisper backend."""

from __future__ import annotations

from typing import Dict, Iterable

import pytest
from fastapi.testclient import TestClient
from datetime import datetime

from app.api import dependencies as dependency_cache
from app.api.dependencies import (
    get_attempts_service,
    get_database_manager,
    get_items_service,
    get_metadata_service,
    get_stats_service,
    get_tags_service,
    get_tts_engine,
    get_tts_engine_manager,
    get_translation_manager,
)
from app.api.routes import attempts as attempts_routes
from app.api.routes import items as items_routes
from app.api.routes import metadata as metadata_routes
from app.api.routes import stats as stats_routes
from app.api.routes import translations as translations_routes
from app.core.config import settings
from app.core.security import reset_rate_limiter_state
from app.main import app
from app.models.database_manager import Base, DatabaseManager
from app.services.attempts_service import AttemptsService
from app.services.item_audio_manager import ItemAudioManager
from app.services.items_service import ItemsService
from app.services.metadata_service import MetadataService
from app.services.stats_service import StatsService
from app.services.tags_service import TagsService


class DummyTaskManager:
    """Minimal stub used to capture submissions in tests."""

    def __init__(self):
        self.is_initialized = True
        self.submissions: list[tuple[tuple, Dict]] = []

    def submit_task_for_item(self, *args, **kwargs):
        self.submissions.append((args, kwargs))
        # Simulate a successful submission by default
        return kwargs.get("task_id", "test-task")

    def start_monitoring(self):  # pragma: no cover - not used in tests
        return None

    def stop_monitoring(self):  # pragma: no cover - not used in tests
        return None


class DummyTTSEngine:
    """Simple TTS engine stub exposing the attributes health checks expect."""

    def __init__(self, initialized: bool = True):
        self.is_initialized = initialized

    def initialize(self):  # pragma: no cover - not used in tests
        self.is_initialized = True

    def shutdown(self):  # pragma: no cover - not used in tests
        self.is_initialized = False


class DummyTranslationManager:
    """Stub translation manager to avoid real provider calls."""

    def __init__(self):
        self.calls = []

    def translate_item(
        self, item_id: int, target_lang: str, force_refresh: bool = False
    ):
        self.calls.append(("translate", item_id, target_lang, force_refresh))
        # block same-lang
        if target_lang == "fi":
            return None
        return {
            "translation_id": 1,
            "item_id": item_id,
            "text": "hello",
            "source_lang": "fi",
            "target_lang": target_lang,
            "translated_text": "hola",
            "provider": "stub",
            "cached": False,
            "status": "completed",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "last_refreshed_at": datetime.now(),
            "metadata": {},
        }

    def get_cached_translation(self, item_id: int, target_lang: str):
        self.calls.append(("cached", item_id, target_lang))
        return None

    def refresh_translation(self, translation_id: int):  # pragma: no cover
        self.calls.append(("refresh", translation_id))
        return None


@pytest.fixture(autouse=True)
def reset_dependency_singletons():
    """Ensure global dependency caches do not leak between tests."""

    dependency_cache.reset_dependency_caches()
    reset_rate_limiter_state()
    yield
    dependency_cache.reset_dependency_caches()
    reset_rate_limiter_state()


@pytest.fixture(scope="session")
def test_db_url(tmp_path_factory: pytest.TempPathFactory) -> str:
    db_path = tmp_path_factory.mktemp("db") / "test.sqlite"
    return f"sqlite:///{db_path}"


@pytest.fixture()
def db_manager(test_db_url: str) -> Iterable[DatabaseManager]:
    manager = DatabaseManager(test_db_url)
    Base.metadata.drop_all(bind=manager.engine)
    Base.metadata.create_all(bind=manager.engine)
    try:
        yield manager
    finally:
        manager.close()


@pytest.fixture()
def tags_service(db_manager: DatabaseManager) -> TagsService:
    return TagsService(db_manager)


@pytest.fixture()
def task_manager() -> DummyTaskManager:
    return DummyTaskManager()


@pytest.fixture()
def translation_manager() -> DummyTranslationManager:
    return DummyTranslationManager()


@pytest.fixture()
def dummy_tts_engine() -> DummyTTSEngine:
    return DummyTTSEngine()


@pytest.fixture()
def items_service(
    db_manager: DatabaseManager, task_manager: DummyTaskManager
) -> Iterable[ItemsService]:
    audio_manager = ItemAudioManager(db_manager, task_manager)
    service = ItemsService(db_manager, task_manager, audio_manager)
    try:
        yield service
    finally:
        audio_manager.shutdown()


@pytest.fixture()
def attempts_service(db_manager: DatabaseManager) -> AttemptsService:
    return AttemptsService(db_manager)


@pytest.fixture()
def stats_service(db_manager: DatabaseManager) -> StatsService:
    return StatsService(db_manager)


@pytest.fixture()
def test_client(
    db_manager: DatabaseManager,
    items_service: ItemsService,
    attempts_service: AttemptsService,
    stats_service: StatsService,
    tags_service: TagsService,
    task_manager: DummyTaskManager,
    dummy_tts_engine: DummyTTSEngine,
    translation_manager: DummyTranslationManager,
):
    settings.api_keys = ["test-suite-key"]

    overrides = {
        get_database_manager: lambda: db_manager,
        get_items_service: lambda: items_service,
        get_attempts_service: lambda: attempts_service,
        get_stats_service: lambda: stats_service,
        get_tags_service: lambda: tags_service,
        get_tts_engine_manager: lambda: task_manager,
        get_tts_engine: lambda: dummy_tts_engine,
        get_translation_manager: lambda: translation_manager,
        get_metadata_service: lambda: MetadataService(db_manager, task_manager),
        # Route-level wrappers
        attempts_routes.get_attempts_service: lambda: attempts_service,
        stats_routes.get_stats_service: lambda: stats_service,
        items_routes.get_items_service: lambda: items_service,
        translations_routes.get_translation_manager: lambda: translation_manager,
        metadata_routes.get_metadata_service: lambda: MetadataService(
            db_manager, task_manager
        ),
    }

    app.dependency_overrides.update(overrides)
    client = TestClient(app, raise_server_exceptions=False)

    client.headers.update({settings.api_key_header_name: settings.api_keys[0]})

    try:
        yield client
    finally:
        app.dependency_overrides.clear()
