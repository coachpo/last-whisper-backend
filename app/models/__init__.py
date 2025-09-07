"""Models package for SQLAlchemy models, database manager, and Pydantic schemas."""

# Import database manager
from .database_manager import DatabaseManager, Base

# Import SQLAlchemy models
from .models import Task, Item, Attempt, Tag

# Import Pydantic schemas
from .schemas import (
    # Item schemas
    ItemCreateRequest,
    BulkItemCreateRequest,
    ItemResponse,
    BulkItemCreateResponse,
    ItemListResponse,
    # Attempt schemas
    AttemptCreateRequest,
    AttemptResponse,
    AttemptListResponse,
    # Tag schemas
    TagCreateRequest,
    TagResponse,
    TagListResponse,
    TagUpdateRequest,
    TagUpdateResponse,
    # Difficulty schemas
    DifficultyUpdateRequest,
    DifficultyUpdateResponse,
    # Stats schemas
    StatsSummaryResponse,
    PracticeLogEntry,
    PracticeLogResponse,
    # Health and error schemas
    HealthResponse,
    HealthCheckResponse,
    ErrorResponse,
)

__all__ = [
    # SQLAlchemy models
    "Task",
    "Item",
    "Attempt",
    "Tag",
    # Database manager
    "DatabaseManager",
    "Base",
    # Item schemas
    "ItemCreateRequest",
    "BulkItemCreateRequest",
    "ItemResponse",
    "BulkItemCreateResponse",
    "ItemListResponse",
    # Attempt schemas
    "AttemptCreateRequest",
    "AttemptResponse",
    "AttemptListResponse",
    # Tag schemas
    "TagCreateRequest",
    "TagResponse",
    "TagListResponse",
    "TagUpdateRequest",
    "TagUpdateResponse",
    # Difficulty schemas
    "DifficultyUpdateRequest",
    "DifficultyUpdateResponse",
    # Stats schemas
    "StatsSummaryResponse",
    "PracticeLogEntry",
    "PracticeLogResponse",
    # Health and error schemas
    "HealthResponse",
    "HealthCheckResponse",
    "ErrorResponse",
]
