"""FastAPI dependencies."""

from functools import lru_cache

from app.core.config import settings
from app.models.database_manager import DatabaseManager
from app.services.attempts_service import AttemptsService
from app.services.item_audio_manager import ItemAudioManager
from app.services.items_service import ItemsService
from app.services.metadata_service import MetadataService
from app.services.stats_service import StatsService
from app.services.tags_service import TagsService
from app.services.task_service import TaskService
from app.tts_engine.tts_engine_manager import TTSEngineManager
from app.tts_engine.tts_engine_wrapper import TTSEngineWrapper
from app.translation.translation_manager import TranslationManager
from app.translation.translation_wrapper import TranslationServiceWrapper


@lru_cache
def get_database_manager() -> DatabaseManager:
    return DatabaseManager(settings.database_url)


@lru_cache
def get_tts_engine() -> TTSEngineWrapper:
    return TTSEngineWrapper()


@lru_cache
def get_tts_engine_manager() -> TTSEngineManager:
    wrapper = get_tts_engine()
    return TTSEngineManager(
        settings.database_url,
        wrapper._service if wrapper.is_initialized else None,
    )


@lru_cache
def get_item_audio_manager() -> ItemAudioManager:
    return ItemAudioManager(get_database_manager(), get_tts_engine_manager())


@lru_cache
def get_items_service() -> ItemsService:
    return ItemsService(
        get_database_manager(),
        get_tts_engine_manager(),
        get_item_audio_manager(),
    )


@lru_cache
def get_attempts_service() -> AttemptsService:
    return AttemptsService(get_database_manager())


@lru_cache
def get_stats_service() -> StatsService:
    return StatsService(get_database_manager())


@lru_cache
def get_tags_service() -> TagsService:
    return TagsService(get_database_manager())


@lru_cache
def get_translation_manager() -> TranslationManager:
    provider_wrapper = TranslationServiceWrapper()
    return TranslationManager(
        settings.database_url,
        provider_wrapper,
        db_manager=get_database_manager(),
    )


@lru_cache
def get_metadata_service() -> MetadataService:
    return MetadataService(get_database_manager(), get_tts_engine_manager())


@lru_cache
def get_task_service() -> TaskService:
    return TaskService()


def reset_dependency_caches() -> None:
    """Utility for tests to clear cached singletons."""

    get_database_manager.cache_clear()
    get_tts_engine.cache_clear()
    get_tts_engine_manager.cache_clear()
    get_item_audio_manager.cache_clear()
    get_items_service.cache_clear()
    get_attempts_service.cache_clear()
    get_stats_service.cache_clear()
    get_tags_service.cache_clear()
    get_translation_manager.cache_clear()
    get_metadata_service.cache_clear()
    get_task_service.cache_clear()
