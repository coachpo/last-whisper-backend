"""SQLAlchemy database models."""
import json
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, DateTime, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

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
    created_at = Column(DateTime, default=datetime.utcnow)
    submitted_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    failed_at = Column(DateTime)
    error_message = Column(Text)
    file_size = Column(Integer)
    sampling_rate = Column(Integer)
    device = Column(String)
    task_metadata = Column("metadata", Text)  # JSON string

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


class DatabaseManager:
    """Database session manager for SQLAlchemy 2.x."""

    def __init__(self, database_url: str = settings.database_url):
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        # Create tables if they don't exist
        Base.metadata.create_all(bind=self.engine)

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
