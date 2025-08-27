"""Application configuration settings."""

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # API Settings
    app_name: str = "Dictation Training Backend"
    app_version: str = "1.0.0"
    app_description: str = (
        "Dictation training backend with local TTS, scoring, and session-less workflow"
    )

    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    log_level: str = "info"

    # Database Settings
    database_url: str = "sqlite:///dictation.db"
    db_path: str = "dictation.db"

    # Audio Storage Settings
    audio_dir: str = "audio"
    base_url: str = "http://localhost:8000"  # For building audio URLs

    # TTS Service Settings
    tts_device: Optional[str] = None  # None for auto-detection
    tts_thread_count: int = 1
    tts_supported_languages: list[str] = ["fi"]  # Supported languages for TTS

    # API Settings
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
    openapi_url: str = "/openapi.json"
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


# Global settings instance
settings = Settings()
