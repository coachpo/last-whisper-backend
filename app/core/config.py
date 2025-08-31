"""Application configuration settings."""

import json
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    # Determine if we are in development mode
    environment: str = "development"  # "development" or "production"
    is_development: bool = environment in ["development", "dev", "local"]
    is_production: bool = not is_development

    # API Settings
    app_name: str = "Last Whisper Backend" + (" (Development)" if is_development else "")
    app_version: str = "1.0.0"
    app_description: str = (
        "Last Whisper's backend service - Dictation training with cloud TTS, scoring, and session-less workflow"
    )

    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = is_development
    log_level: str = "info"

    # Database Settings
    database_url: str = "sqlite:///data/dictation.db"

    # Audio Storage Settings
    audio_dir: str = "audio"

    # TTS Service Settings
    tts_supported_languages: list[str] = ["fi"]  # Supported languages for TTS
    tts_provider: str = "gcp"  # TTS provider: 'azure' or 'gcp'/'google'

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
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"  # Comma-separated list of allowed origins
    cors_allow_methods: str = "*"  # Comma-separated list or "*" for all methods
    cors_allow_headers: str = "*"  # Comma-separated list or "*" for all headers

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @field_validator('tts_supported_languages', mode='before')
    @classmethod
    def parse_tts_supported_languages(cls, v):
        """Parse tts_supported_languages from string to list."""
        if isinstance(v, str):
            # Check if it looks like JSON (starts with [ and ends with ])
            if v.strip().startswith('[') and v.strip().endswith(']'):
                try:
                    # Try to parse as JSON
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            # Default to comma-separated parsing (for Docker env vars)
            return [lang.strip() for lang in v.split(',') if lang.strip()]
        return v


# Global settings instance
settings = Settings()
