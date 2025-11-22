"""Database session manager for SQLAlchemy 2.x."""

import os
from typing import Optional, TYPE_CHECKING

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings

if TYPE_CHECKING:
    from .models import Task

Base = declarative_base()


class DatabaseManager:
    """Database session manager for SQLAlchemy 2.x."""

    def __init__(self, database_url: str = settings.database_url):
        # Configure database engine
        if database_url.startswith("sqlite"):
            self._ensure_sqlite_parent_dir(database_url)
            # Add SQLite-specific options
            self.engine = create_engine(
                database_url,
                echo=False,
                connect_args={
                    "check_same_thread": False,
                },
            )

            # Configure basic SQLite pragmas
            @event.listens_for(self.engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                # Enable foreign keys
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        else:
            self.engine = create_engine(database_url, echo=False)

        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

        # Ensure audio directory exists
        os.makedirs(settings.audio_dir, exist_ok=True)

        # Import models to ensure they're registered with Base

        # Create tables if they don't exist
        self._create_tables_if_not_exist()

    def _create_tables_if_not_exist(self):
        """Create tables if they don't exist."""
        # create_all is idempotent - it only creates tables that don't exist
        Base.metadata.create_all(bind=self.engine)

    @staticmethod
    def _ensure_sqlite_parent_dir(database_url: str) -> None:
        url = make_url(database_url)
        db_path = url.database
        if not db_path or db_path == ":memory:":
            return
        parent_dir = os.path.dirname(os.path.abspath(db_path))
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

    def get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()

    def get_task_by_id(self, task_id: str) -> Optional["Task"]:
        """Get a task by its ID."""
        from .models import Task

        with self.get_session() as session:
            return session.query(Task).filter(Task.task_id == task_id).first()

    def get_all_tasks(
        self, status: Optional[str] = None, limit: int = 100
    ) -> list["Task"]:
        """Get all tasks, optionally filtered by status."""
        from .models import Task

        with self.get_session() as session:
            query = session.query(Task)
            if status:
                query = query.filter(Task.status == status)
            return query.order_by(Task.created_at.desc()).limit(limit).all()

    def health_check(self) -> bool:
        """Check if database is accessible."""
        try:
            with self.get_session() as session:
                result = session.execute(text("SELECT 1"))
                result.fetchone()
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

    def close(self):
        """Dispose of the database engine."""
        self.engine.dispose()
