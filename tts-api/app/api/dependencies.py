"""FastAPI dependencies."""
from app.services.database import db_service
from app.services.task_manager import task_manager
from app.services.tts_service import tts_service


def get_database_service():
    """Dependency to get database service."""
    return db_service


def get_task_manager():
    """Dependency to get task manager."""
    return task_manager


def get_tts_service():
    """Dependency to get TTS service."""
    return tts_service
