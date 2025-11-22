"""Unit tests for the metadata aggregation service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.core.runtime_state import set_app_started_at
from app.models.enums import MetadataDetailLevel
from app.services.metadata_service import MetadataService


class _DummyDBManager:
    def __init__(self):
        self.engine = SimpleNamespace(name="sqlite")


class _DummyTTSManager:
    def get_tts_worker_health(self):
        return {"worker_running": True, "queue_size": 0}


def test_metadata_service_returns_core_sections():
    set_app_started_at(datetime.now(timezone.utc) - timedelta(seconds=5))
    service = MetadataService(_DummyDBManager(), _DummyTTSManager(), cache_ttl=1)

    payload = service.get_metadata()

    assert payload.service.name.startswith("Last Whisper")
    assert payload.build.commit
    assert payload.providers.database["engine"] == "sqlite"
    assert payload.runtime is not None
    assert payload.runtime.uptime_seconds >= 0


def test_metadata_service_respects_field_filter():
    service = MetadataService(_DummyDBManager(), _DummyTTSManager(), cache_ttl=1)
    payload = service.get_metadata(
        detail=MetadataDetailLevel.CORE, include_fields={"runtime"}
    )

    assert payload.runtime is not None
    assert payload.build is None


def test_metadata_service_translation_languages_structured():
    service = MetadataService(_DummyDBManager(), _DummyTTSManager(), cache_ttl=1)
    payload = service.get_metadata()

    translation_languages = payload.features.get("translation_languages")
    assert isinstance(translation_languages, list)
    assert translation_languages == [
        {"language_code": "en", "language_name": "English"},
        {"language_code": "fi", "language_name": "Suomi"},
        {"language_code": "zh-CN", "language_name": "简体中文"},
        {"language_code": "zh-TW", "language_name": "繁體中文"},
    ]


def test_metadata_service_provider_translation_languages_structured():
    service = MetadataService(_DummyDBManager(), _DummyTTSManager(), cache_ttl=1)
    payload = service.get_metadata()

    translation_supported = payload.providers.translation["supported_languages"]
    assert translation_supported == [
        {"language_code": "en", "language_name": "English"},
        {"language_code": "fi", "language_name": "Suomi"},
        {"language_code": "zh-CN", "language_name": "简体中文"},
        {"language_code": "zh-TW", "language_name": "繁體中文"},
    ]


def test_metadata_service_provider_tts_languages_structured():
    service = MetadataService(_DummyDBManager(), _DummyTTSManager(), cache_ttl=1)
    payload = service.get_metadata()

    tts_supported = payload.providers.tts["supported_languages"]
    assert tts_supported == [
        {"language_code": "fi", "language_name": "Suomi"},
    ]
