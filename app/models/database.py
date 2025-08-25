"""SQLAlchemy database models."""

import json
import os
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, create_engine, Index, event
from sqlalchemy.orm import Session, declarative_base, sessionmaker, relationship

from app.core.config import settings

Base = declarative_base()


class Task(Base):
    """SQLAlchemy model for TTS tasks, matching existing database schema."""

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String, unique=True, nullable=False, index=True)
    original_text = Column(Text, nullable=False)
    text_hash = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="pending", index=True)
    output_file_path = Column(Text)
    custom_filename = Column(Text)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    submitted_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    failed_at = Column(DateTime)
    error_message = Column(Text)
    file_size = Column(Integer)
    sampling_rate = Column(Integer)
    device = Column(String)
    task_metadata = Column("metadata", Text)  # JSON string
    item_id = Column(Integer, ForeignKey("items.id", ondelete="SET NULL"), nullable=True, index=True)

    # Relationships
    item = relationship("Item", back_populates="task")

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
    tts_status = Column(String(20), nullable=False, default="pending", index=True)
    audio_url = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC), index=True)
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # Relationships
    attempts = relationship("Attempt", back_populates="item", cascade="all, delete-orphan")
    task = relationship("Task", back_populates="item", uselist=False)

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


class Attempt(Base):
    """SQLAlchemy model for dictation attempts."""

    __tablename__ = "attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    percentage = Column(Integer, nullable=False)  # 0-100
    wer = Column(Float, nullable=False)  # 0.0-1.0
    words_ref = Column(Integer, nullable=False)
    words_correct = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC), index=True)

    # Relationships
    item = relationship("Item", back_populates="attempts")


# Define indexes for better query performance
Index('idx_items_locale_difficulty', Item.locale, Item.difficulty)
Index('idx_items_created_at_desc', Item.created_at.desc())
Index('idx_attempts_item_created', Attempt.item_id, Attempt.created_at)


class DatabaseManager:
    """Database session manager for SQLAlchemy 2.x with WAL configuration."""

    def __init__(self, database_url: str = settings.database_url):
        # Configure SQLite engine with WAL mode and other optimizations
        if database_url.startswith("sqlite"):
            # Add SQLite-specific options
            self.engine = create_engine(
                database_url,
                echo=False,
                connect_args={
                    "check_same_thread": False,
                    "timeout": 30,  # 30 second timeout
                },
                pool_pre_ping=True,
                pool_recycle=3600,  # Recycle connections every hour
            )

            # Configure WAL mode and other pragmas
            @event.listens_for(self.engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                # Enable WAL mode for better concurrency
                cursor.execute("PRAGMA journal_mode=WAL")
                # Increase cache size (in KB)
                cursor.execute("PRAGMA cache_size=10000")
                # Enable foreign keys
                cursor.execute("PRAGMA foreign_keys=ON")
                # Set synchronous mode to NORMAL for better performance
                cursor.execute("PRAGMA synchronous=NORMAL")
                # Set busy timeout to 30 seconds
                cursor.execute("PRAGMA busy_timeout=30000")
                cursor.close()
        else:
            self.engine = create_engine(database_url, echo=False)

        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        # Ensure audio directory exists
        os.makedirs(settings.audio_dir, exist_ok=True)

        # Create tables if they don't exist
        Base.metadata.create_all(bind=self.engine)

        # Setup FTS5 virtual table for text search
        self._setup_fts5()

    def get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()

    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """Get a task by its ID."""
        with self.get_session() as session:
            return session.query(Task).filter(Task.task_id == task_id).first()

    def get_all_tasks(self, status: Optional[str] = None, limit: int = 100) -> list[Task]:
        """Get all tasks, optionally filtered by status."""
        with self.get_session() as session:
            query = session.query(Task)
            if status:
                query = query.filter(Task.status == status)
            return query.order_by(Task.created_at.desc()).limit(limit).all()

    def health_check(self) -> bool:
        """Check if database is accessible."""
        try:
            with self.get_session() as session:
                # Simple query to test connection
                session.execute("SELECT 1").fetchone()
                return True
        except Exception:
            return False

    def check_audio_directory(self) -> bool:
        """Check if audio directory is writable."""
        try:
            test_file = os.path.join(settings.audio_dir, ".write_test")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            return True
        except Exception:
            return False

    def _setup_fts5(self):
        """Setup FTS5 virtual table for text search."""
        if not self.engine.url.database or not self.engine.url.database.endswith('.db'):
            return  # Only for SQLite databases

        try:
            with self.get_session() as session:
                # Create FTS5 virtual table if it doesn't exist
                session.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5(
                        id UNINDEXED,
                        text,
                        content='items',
                        content_rowid='id'
                    )
                """)

                # Create triggers to keep FTS table in sync
                session.execute("""
                                CREATE TRIGGER IF NOT EXISTS items_ai
                                    AFTER INSERT
                                    ON items
                                BEGIN
                                    INSERT INTO items_fts(id, text) VALUES (new.id, new.text);
                                END
                                """)

                session.execute("""
                                CREATE TRIGGER IF NOT EXISTS items_au
                                    AFTER UPDATE
                                    ON items
                                BEGIN
                                    UPDATE items_fts SET text = new.text WHERE id = new.id;
                                END
                                """)

                session.execute("""
                                CREATE TRIGGER IF NOT EXISTS items_ad
                                    AFTER DELETE
                                    ON items
                                BEGIN
                                    DELETE FROM items_fts WHERE id = old.id;
                                END
                                """)

                session.commit()
        except Exception as e:
            print(f"Warning: Could not setup FTS5: {e}")

    def rebuild_fts_index(self):
        """Rebuild the FTS5 index from existing data."""
        try:
            with self.get_session() as session:
                # Clear and rebuild FTS index
                session.execute("DELETE FROM items_fts")
                session.execute("""
                                INSERT INTO items_fts(id, text)
                                SELECT id, text
                                FROM items
                                """)
                session.commit()
        except Exception as e:
            print(f"Warning: Could not rebuild FTS index: {e}")
