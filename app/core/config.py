"""Application configuration settings."""

from typing import ClassVar, Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    _app_name_base: ClassVar[str] = "Last Whisper Backend"

    # Determine if we are in development mode
    environment: str = "development"  # "development" or "production"
    is_development: bool = True
    is_production: bool = False

    # API Settings
    app_name: str = _app_name_base
    app_version: str = "1.0.0"
    app_description: str = (
        "Last Whisper's backend service - Dictation training with cloud TTS, scoring, and session-less workflow"
    )

    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000
    reload: Optional[bool] = None
    log_level: str = "info"

    # Database Settings
    database_url: str = "sqlite:///data/dictation.db"

    # Audio Storage Settings
    audio_dir: str = "audio"

    # Translation Settings
    translation_provider: str = "google"  # Currently supports 'google'
    translation_supported_languages: list[str] = ["en", "fi", "zh-CN", "zh-TW"]

    # TTS Service Settings
    tts_supported_languages: list[str] = ["fi"]  # Supported languages for TTS
    tts_provider: str = "gcp"  # TTS provider: 'azure' or 'gcp'/'google'
    tts_submission_workers: int = 4

    # Google Cloud Settings
    google_application_credentials: Optional[str] = "keys/google-credentials.json"

    # Azure Settings (optional)
    azure_speech_key: Optional[str] = None
    azure_speech_region: Optional[str] = None

    # API Settings
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
    openapi_url: str = "/openapi.json"

    # CORS Settings
    cors_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000"  # Comma-separated list of allowed origins
    )
    cors_allow_methods: str = "*"  # Comma-separated list or "*" for all methods
    cors_allow_headers: str = "*"  # Comma-separated list or "*" for all headers

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @model_validator(mode="after")
    def _set_environment_flags(self):
        env = (self.environment or "").strip().lower()
        self.is_development = env in {"development", "dev", "local"}
        self.is_production = not self.is_development
        if self.reload is None:
            self.reload = self.is_development

        # Only auto-append the development suffix when using the default base name
        if self.app_name in {
            self._app_name_base,
            f"{self._app_name_base} (Development)",
        }:
            suffix = " (Development)" if self.is_development else ""
            self.app_name = f"{self._app_name_base}{suffix}"

        return self


# Global settings instance
settings = Settings()
