"""FastAPI dependencies."""

from app.core.config import settings
from app.models.database_manager import DatabaseManager
from app.services.attempts_service import AttemptsService
from app.services.items_service import ItemsService
from app.services.stats_service import StatsService
from app.services.tags_service import TagsService
from app.services.task_service import TaskService
from app.tts_engine.tts_engine_manager import TTSEngineManager
from app.tts_engine.tts_engine_wrapper import TTSEngineWrapper
from app.translation.translation_manager import TranslationManager
from app.translation.translation_wrapper import TranslationServiceWrapper

# Global instances
_database_manager = None
_items_service = None
_attempts_service = None
_stats_service = None
_task_manager = None
_tts_engine = None
_task_service = None
_tags_service = None
_translation_manager = None


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
        engine_manager = get_tts_engine_manager()
        _items_service = ItemsService(db_manager, engine_manager)
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


def get_tts_engine_manager() -> TTSEngineManager:
    """Dependency to get unified task manager."""
    global _task_manager
    if _task_manager is None:
        tts_service = get_tts_engine()
        _task_manager = TTSEngineManager(
            settings.database_url,
            tts_service._service if tts_service.is_initialized else None,
        )
    return _task_manager


def get_tts_engine() -> TTSEngineWrapper:
    """Dependency to get TTS engine."""
    global _tts_engine
    if _tts_engine is None:
        _tts_engine = TTSEngineWrapper()
    return _tts_engine


def get_tags_service() -> TagsService:
    """Dependency to get tags service."""
    global _tags_service
    if _tags_service is None:
        db_manager = get_database_manager()
        _tags_service = TagsService(db_manager)
    return _tags_service


def get_translation_manager() -> TranslationManager:
    """Dependency to get translation manager."""
    global _translation_manager
    if _translation_manager is None:
        provider_wrapper = TranslationServiceWrapper()
        _translation_manager = TranslationManager(
            settings.database_url, provider_wrapper
        )
    return _translation_manager


# Legacy dependencies for backward compatibility
def get_task_service() -> TaskService:
    """Dependency to get database service."""
    global _task_service
    if _task_service is None:
        _task_service = TaskService()
    return _task_service
