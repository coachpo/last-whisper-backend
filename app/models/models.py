"""SQLAlchemy database models."""

import json
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

# Import Base from database_manager to avoid circular imports
from .database_manager import Base
from .enums import TaskStatus, ItemTTSStatus, TaskKind


class Task(Base):
    """SQLAlchemy model for TTS tasks, matching existing database schema."""

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String, unique=True, nullable=False, index=True)
    original_text = Column(Text, nullable=False)
    text_hash = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default=TaskStatus.PENDING, index=True)
    output_file_path = Column(Text)
    custom_filename = Column(Text)
    task_kind = Column(String, nullable=False, default=TaskKind.GENERATE, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    submitted_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    failed_at = Column(DateTime)
    error_message = Column(Text)
    file_size = Column(Integer)
    sampling_rate = Column(Integer)
    device = Column(String)
    task_metadata = Column("metadata", Text)  # JSON string

    # Relationships
    items = relationship("Item", back_populates="task")

    @property
    def metadata_dict(self) -> dict:
        """Parse metadata JSON string to dict."""
        if self.task_metadata:
            try:
                return json.loads(self.task_metadata)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    @property
    def duration(self) -> Optional[float]:
        """Calculate audio duration from metadata."""
        metadata = self.metadata_dict
        return metadata.get("duration")


class Item(Base):
    """SQLAlchemy model for dictation items."""

    __tablename__ = "items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    locale = Column(String(10), nullable=False, index=True)
    text = Column(Text, nullable=False)
    difficulty = Column(Integer, nullable=True, index=True)
    tags_json = Column(Text, nullable=True)  # JSON array of strings
    task_id = Column(
        String,
        ForeignKey("tasks.task_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(DateTime, nullable=False, default=datetime.now, index=True)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    # Relationships
    attempts = relationship(
        "Attempt", back_populates="item", cascade="all, delete-orphan"
    )
    task = relationship("Task", back_populates="items")
    tts_record = relationship(
        "ItemTTS", back_populates="item", uselist=False, cascade="all, delete-orphan"
    )
    translations = relationship(
        "Translation", back_populates="item", cascade="all, delete-orphan"
    )

    @property
    def tags(self) -> list[str]:
        """Parse tags JSON string to list."""
        if self.tags_json:
            try:
                return json.loads(self.tags_json)
            except (json.JSONDecodeError, TypeError):
                return []
        return []

    @tags.setter
    def tags(self, value: list[str]):
        """Set tags as JSON string."""
        self.tags_json = json.dumps(value) if value else None

    @property
    def has_attempts(self) -> bool:
        """Check if item has any attempts."""
        return len(self.attempts) > 0


class ItemTTS(Base):
    """Stores TTS status per item (decoupled from Item)."""

    __tablename__ = "item_tts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(
        Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    task_id = Column(
        String,
        ForeignKey("tasks.task_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status = Column(
        String(20), nullable=False, default=ItemTTSStatus.PENDING, index=True
    )
    created_at = Column(DateTime, nullable=False, default=datetime.now, index=True)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    # Relationships
    item = relationship("Item", back_populates="tts_record")
    task = relationship("Task")


class Translation(Base):
    """Cached translations for items."""

    __tablename__ = "translations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(
        Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_lang = Column(String(10), nullable=False, index=True)
    source_lang = Column(String(10), nullable=False, index=True)
    text_hash = Column(String(32), nullable=False, index=True)
    translated_text = Column(Text, nullable=True)
    provider = Column(String(32), nullable=False, default="google", index=True)
    status = Column(String(16), nullable=False, default=TaskStatus.PENDING, index=True)
    error = Column(Text, nullable=True)
    translation_metadata = Column("metadata", Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now, index=True)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )
    last_refreshed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("item_id", "target_lang", name="uq_translation_item_target"),
    )

    # Relationships
    item = relationship("Item", back_populates="translations")

    @property
    def metadata_dict(self) -> dict:
        if self.translation_metadata:
            try:
                return json.loads(self.translation_metadata)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}


class Attempt(Base):
    """SQLAlchemy model for dictation attempts."""

    __tablename__ = "attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(
        Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    text = Column(Text, nullable=False)
    percentage = Column(Integer, nullable=False)  # 0-100
    wer = Column(Float, nullable=False)  # 0.0-1.0
    words_ref = Column(Integer, nullable=False)
    words_correct = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now, index=True)

    # Relationships
    item = relationship("Item", back_populates="attempts")


class Tag(Base):
    """SQLAlchemy model for preset tags."""

    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self):
        return f"<Tag(id={self.id}, name='{self.name}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# Define indexes for better query performance
Index("idx_items_locale_difficulty", Item.locale, Item.difficulty)
Index("idx_items_created_at_desc", Item.created_at.desc())
Index("idx_items_created_at_asc", Item.created_at.asc())
Index("idx_attempts_item_created", Attempt.item_id, Attempt.created_at)
Index("idx_itemtts_status", ItemTTS.status)
Index("idx_itemtts_item", ItemTTS.item_id)
Index("idx_translations_item_status", Translation.item_id, Translation.status)
Index("idx_translations_target", Translation.target_lang)
