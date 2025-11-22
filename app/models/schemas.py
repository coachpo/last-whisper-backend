"""Pydantic models for API request/response schemas."""

from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, field_validator

from .enums import ItemTTSStatus, TaskStatus


class ErrorResponse(BaseModel):
    """Response model for API errors."""

    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Additional error details")


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str = Field(..., description="Health status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    timestamp: datetime = Field(..., description="Current timestamp")


class MetadataServiceInfo(BaseModel):
    """High-level identifiers for the application."""

    name: str = Field(..., description="Application name")
    description: str = Field(..., description="Human-friendly description")
    environment: str = Field(..., description="Deployment environment label")
    version: str = Field(..., description="Semantic application version")
    schema_version: str = Field(..., description="Metadata schema revision")


class MetadataBuildInfo(BaseModel):
    """Build and artifact identifiers."""

    commit: str = Field(..., description="Full git SHA or image ID")
    short_commit: str = Field(..., description="Abbreviated commit identifier")
    branch: str = Field(..., description="Source branch name")
    built_at: Optional[str] = Field(None, description="Build timestamp (ISO 8601)")
    python_version: str = Field(..., description="Python interpreter version")
    fastapi_version: str = Field(..., description="FastAPI library version")


class MetadataRuntimeInfo(BaseModel):
    """Process runtime state."""

    started_at: datetime = Field(..., description="Process bootstrap timestamp")
    uptime_seconds: float = Field(..., description="Seconds since startup")
    process_id: int = Field(..., description="Operating system process ID")
    host: str = Field(..., description="Hostname handling the request")
    worker: Dict[str, Any] = Field(
        default_factory=dict,
        description="Aggregated worker/queue stats when available",
    )


class MetadataProvidersSection(BaseModel):
    """External provider wiring summary."""

    database: Dict[str, Any] = Field(default_factory=dict)
    tts: Dict[str, Any] = Field(default_factory=dict)
    translation: Dict[str, Any] = Field(default_factory=dict)


class ApplicationMetadataResponse(BaseModel):
    """Envelope for the /metadata endpoint."""

    service: MetadataServiceInfo
    build: Optional[MetadataBuildInfo] = None
    runtime: Optional[MetadataRuntimeInfo] = None
    providers: Optional[MetadataProvidersSection] = None
    features: Dict[str, Any] = Field(default_factory=dict)
    limits: Dict[str, Any] = Field(default_factory=dict)
    links: Dict[str, str] = Field(default_factory=dict)


# New schemas for dictation API


class ItemCreateRequest(BaseModel):
    """Request model for creating a new dictation item."""

    locale: str = Field(
        ...,
        min_length=2,
        max_length=10,
        description="Language locale (e.g., 'en', 'fi')",
    )
    text: str = Field(
        ..., min_length=1, max_length=10000, description="Text for dictation practice"
    )
    difficulty: Optional[int] = Field(
        None,
        ge=1,
        le=5,
        description="Difficulty level (1-5). If not provided, will be auto-calculated based on text length.",
    )
    tags: Optional[List[str]] = Field(None, description="Tags for categorization")

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v):
        """Validate tags."""
        if v is not None:
            if len(v) > 20:
                raise ValueError("Maximum 20 tags allowed")
            for tag in v:
                if not tag or len(tag.strip()) == 0:
                    raise ValueError("Tags cannot be empty")
                if len(tag) > 50:
                    raise ValueError("Tag length cannot exceed 50 characters")
        return v


class BulkItemCreateRequest(BaseModel):
    """Request model for creating multiple dictation items."""

    items: List[ItemCreateRequest] = Field(
        ..., min_length=1, max_length=100, description="List of items to create"
    )

    @field_validator("items")
    @classmethod
    def validate_items_not_empty(cls, v):
        """Validate that individual item requests are not empty."""
        if not v:
            raise ValueError("Items list cannot be empty")
        if len(v) > 100:
            raise ValueError("Maximum 100 items allowed per request")
        return v


class TagUpdateRequest(BaseModel):
    """Request model for updating item tags."""

    tags: List[str] = Field(
        default_factory=list, description="New tags to replace all existing tags"
    )


class TagUpdateResponse(BaseModel):
    """Response model for tag update operation."""

    item_id: int = Field(..., description="Item ID")
    operation: str = Field(..., description="Operation performed")
    previous_tags: List[str] = Field(..., description="Tags before update")
    current_tags: List[str] = Field(..., description="Tags after update")
    updated_at: datetime = Field(..., description="Update timestamp")
    message: str = Field(..., description="Description of the operation performed")


class DifficultyUpdateRequest(BaseModel):
    """Request model for updating item difficulty."""

    difficulty: int = Field(..., ge=1, le=5, description="Difficulty level (1-5)")


class DifficultyUpdateResponse(BaseModel):
    """Response model for difficulty update operation."""

    item_id: int = Field(..., description="Item ID")
    previous_difficulty: Optional[int] = Field(
        None, description="Difficulty before update"
    )
    current_difficulty: int = Field(..., description="Difficulty after update")
    updated_at: datetime = Field(..., description="Update timestamp")
    message: str = Field(..., description="Description of the operation performed")


class ItemResponse(BaseModel):
    """Response model for dictation item."""

    id: int = Field(..., description="Item ID")
    locale: str = Field(..., description="Language locale")
    text: str = Field(..., description="Text for dictation")
    difficulty: Optional[int] = Field(None, description="Difficulty level")
    tags: List[str] = Field(default_factory=list, description="Tags")
    tts_status: Optional[ItemTTSStatus] = Field(
        None, description="TTS status: pending, ready, failed"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    practiced: bool = Field(..., description="Whether item has been practiced")


class ItemTTSStatusResponse(BaseModel):
    """Response model for item TTS status."""

    item_id: int = Field(..., description="Item ID")
    text: str = Field(..., description="Preview of the item text")
    tts_status: ItemTTSStatus = Field(..., description="Current TTS status")
    created_at: Optional[datetime] = Field(
        None, description="When the item was created"
    )
    updated_at: Optional[datetime] = Field(
        None, description="When the item was last updated"
    )


class BulkItemCreateResponse(BaseModel):
    """Response model for bulk item creation."""

    created_items: List[ItemResponse] = Field(..., description="List of created items")
    total_created: int = Field(..., description="Total number of items created")
    failed_items: List[Dict[str, Any]] = Field(
        default_factory=list, description="List of failed items with error details"
    )
    total_failed: int = Field(
        ..., description="Total number of items that failed to create"
    )
    submitted_at: datetime = Field(
        ..., description="Timestamp when the bulk creation was submitted"
    )


class ItemListResponse(BaseModel):
    """Response model for item list."""

    items: List[ItemResponse] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")


class AttemptCreateRequest(BaseModel):
    """Request model for creating an attempt."""

    item_id: int = Field(..., description="Item ID")
    text: str = Field(
        ..., min_length=0, max_length=10000, description="User's dictation attempt"
    )


class AttemptResponse(BaseModel):
    """Response model for dictation attempt."""

    id: int = Field(..., description="Attempt ID")
    item_id: int = Field(..., description="Item ID")
    text: str = Field(..., description="User's attempt text")
    percentage: int = Field(..., description="Score percentage (0-100)")
    wer: float = Field(..., description="Word Error Rate (0.0-1.0)")
    words_ref: int = Field(..., description="Number of words in reference")
    words_correct: int = Field(..., description="Number of correct words")
    created_at: datetime = Field(..., description="Attempt timestamp")


class AttemptListResponse(BaseModel):
    """Response model for attempt list."""

    attempts: List[AttemptResponse] = Field(..., description="List of attempts")
    total: int = Field(..., description="Total number of attempts")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")


class StatsSummaryResponse(BaseModel):
    """Response model for summary statistics."""

    total_attempts: int = Field(..., description="Total number of attempts")
    unique_items_practiced: int = Field(
        ..., description="Number of unique items practiced"
    )
    average_score: float = Field(..., description="Average score percentage")
    best_score: int = Field(..., description="Best score percentage")
    worst_score: int = Field(..., description="Worst score percentage")
    total_practice_time_minutes: float = Field(
        ..., description="Total practice time in minutes"
    )


class PracticeLogEntry(BaseModel):
    """Entry in practice log."""

    item_id: int = Field(..., description="Item ID")
    text: str = Field(..., description="Item text")
    locale: str = Field(..., description="Language locale")
    difficulty: int = Field(..., description="Difficulty level")
    tags: List[str] = Field(default_factory=list, description="Tags")
    attempt_count: int = Field(..., description="Number of attempts")
    first_attempt_at: Optional[datetime] = Field(
        None, description="First attempt timestamp"
    )
    last_practiced_at: Optional[datetime] = Field(
        None, description="Last practice timestamp"
    )
    average_score: float = Field(..., description="Average score percentage")
    best_score: int = Field(..., description="Best score percentage")
    worst_score: int = Field(..., description="Worst score percentage")
    avg_wer: float = Field(..., description="Average Word Error Rate")


class PracticeLogResponse(BaseModel):
    """Response model for practice log."""

    practice_log: List[PracticeLogEntry] = Field(
        ..., description="Practice log entries"
    )
    total: int = Field(..., description="Total number of entries")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")


class HealthCheckResponse(BaseModel):
    """Response model for health check."""

    status: str = Field(..., description="Overall health status")
    checks: dict = Field(..., description="Individual health checks")


# Translation schemas (item-bound only)


class ItemTranslationCreateRequest(BaseModel):
    """Request to translate an item to a target language."""

    target_lang: str = Field(..., min_length=2, max_length=10, description="Target language code")
    force_refresh: bool = Field(False, description="If true, bypass cache and refresh from provider")


class ItemTranslationQuery(BaseModel):
    """Query params for fetching a cached translation."""

    target_lang: str = Field(..., min_length=2, max_length=10, description="Target language code")


class TranslationResponse(BaseModel):
    """Response model for translations."""

    translation_id: int = Field(..., description="Translation record ID")
    item_id: int = Field(..., description="Linked item ID")
    text: str = Field(..., description="Original item text")
    source_lang: str = Field(..., description="Source language (from item locale)")
    target_lang: str = Field(..., description="Target language")
    translated_text: Optional[str] = Field(None, description="Translated text")
    provider: str = Field(..., description="Provider used (e.g., google)")
    cached: bool = Field(..., description="Whether served from cache")
    status: TaskStatus = Field(..., description="Status of translation task")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_refreshed_at: Optional[datetime] = Field(
        None, description="When the translation was last refreshed from provider"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Provider-specific metadata (e.g., detected language, model)"
    )


class TranslationRefreshResponse(TranslationResponse):
    """Response for refresh operations (same shape as TranslationResponse)."""

    cached: bool = Field(False, description="Refresh always returns a fresh provider result")


# Audio refresh schemas


class AudioRefreshResponse(BaseModel):
    """Response for forcing audio regeneration."""

    item_id: int = Field(..., description="Item ID")
    task_id: str = Field(..., description="Queued TTS task identifier")
    status: TaskStatus = Field(..., description="Task status at submission time")
    tts_status: ItemTTSStatus = Field(..., description="Item-level TTS status after enqueue")
    audio_path: Optional[str] = Field(
        None, description="Expected audio file path once generation completes"
    )
    provider: str = Field(..., description="TTS provider used")
    voice: Optional[str] = Field(None, description="Voice used (if available)")
    cached: bool = Field(False, description="Audio served from cache; false on refresh")
    created_at: Optional[datetime] = Field(None, description="Item created timestamp")
    updated_at: Optional[datetime] = Field(None, description="Item updated timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional provider metadata")


# Tag schemas for preset tags


class TagCreateRequest(BaseModel):
    """Request model for creating a new preset tag."""

    name: str = Field(..., min_length=1, max_length=50, description="Tag name")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        """Validate tag name."""
        if not v or not v.strip():
            raise ValueError("Tag name cannot be empty")
        return v.strip()


class TagResponse(BaseModel):
    """Response model for preset tag."""

    id: int = Field(..., description="Tag ID")
    name: str = Field(..., description="Tag name")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class TagListResponse(BaseModel):
    """Response model for tag list."""

    tags: List[TagResponse] = Field(..., description="List of tags")
    total: int = Field(..., description="Total number of tags")
