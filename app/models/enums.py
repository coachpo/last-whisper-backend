"""Centralized enum definitions for status fields."""

from enum import Enum


class TaskStatus(str, Enum):
    """Enum for Task model status field."""

    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DONE = "done"


class ItemTTSStatus(str, Enum):
    """Enum for Item model tts_status field."""

    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"


class MetadataDetailLevel(str, Enum):
    """Controls how much information the metadata endpoint returns."""

    CORE = "core"
    RUNTIME = "runtime"
    FULL = "full"
