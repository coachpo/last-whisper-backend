"""Tests for application configuration helpers."""

from app.core.config import Settings


def test_settings_production_flags():
    settings = Settings(environment="production", cors_origins="https://example.com")

    assert settings.is_development is False
    assert settings.is_production is True
    assert settings.reload is False
    assert settings.app_name == "Last Whisper Backend"


def test_settings_development_flags():
    settings = Settings(environment="dev")

    assert settings.is_development is True
    assert settings.is_production is False
    assert settings.reload is True
    assert settings.app_name.endswith(" (Development)")
