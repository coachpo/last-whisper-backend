"""Application configuration settings."""
import os
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # API Settings
    app_name: str = "TTS API"
    app_version: str = "1.0.0"
    app_description: str = "Text-to-Speech conversion API that orchestrates with existing TTS services"
    
    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    log_level: str = "info"
    
    # Database Settings
    database_url: str = "sqlite:///tts_tasks.db"
    
    # TTS Service Settings
    tts_output_dir: str = "output"
    tts_device: Optional[str] = None  # None for auto-detection
    
    # API Settings
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
    openapi_url: str = "/openapi.json"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
