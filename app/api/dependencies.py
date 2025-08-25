"""FastAPI dependencies."""

from app.core.config import settings
from app.models.database import DatabaseManager
from app.services.attempts_service import AttemptsService
from app.services.database import db_service
from app.services.item_task_manager import ItemTaskManager
from app.services.items_service import ItemsService
from app.services.outer.tts_service import tts_service
from app.services.stats_service import StatsService
from app.services.task_manager import task_manager

# Global instances
_database_manager = None
_items_service = None
_attempts_service = None
_stats_service = None
_item_task_manager = None


def get_database_manager() -> DatabaseManager:
    """Dependency to get database manager."""
    global _database_manager
    if _database_manager is None:
        _database_manager = DatabaseManager()
    return _database_manager


def get_items_service() -> ItemsService:
    """Dependency to get items service."""
    global _items_service
    if _items_service is None:
        db_manager = get_database_manager()
        _items_service = ItemsService(db_manager, tts_service)
    return _items_service


def get_attempts_service() -> AttemptsService:
    """Dependency to get attempts service."""
    global _attempts_service
    if _attempts_service is None:
        db_manager = get_database_manager()
        _attempts_service = AttemptsService(db_manager)
    return _attempts_service


def get_stats_service() -> StatsService:
    """Dependency to get stats service."""
    global _stats_service
    if _stats_service is None:
        db_manager = get_database_manager()
        _stats_service = StatsService(db_manager)
    return _stats_service


def get_item_task_manager() -> ItemTaskManager:
    """Dependency to get item task manager."""
    global _item_task_manager
    if _item_task_manager is None:
        _item_task_manager = ItemTaskManager(settings.database_url,
                                                 tts_service._service if tts_service.is_initialized else None)
    return _item_task_manager


# Legacy dependencies for backward compatibility
def get_database_service():
    """Dependency to get database service."""
    return db_service


def get_task_manager():
    """Dependency to get task manager."""
    return task_manager


def get_tts_service():
    """Dependency to get TTS service."""
    return tts_service
