"""Database service layer."""
from typing import Optional, List

from app.core.config import settings
from app.core.exceptions import DatabaseException, TaskNotFoundException
from app.models.database import DatabaseManager, Task


class DatabaseService:
    """Service for database operations."""

    def __init__(self):
        self.db_manager = DatabaseManager(settings.database_url)

    def get_task_by_id(self, task_id: str) -> Task:
        """Get a task by ID, raising exception if not found."""
        task = self.db_manager.get_task_by_id(task_id)
        if not task:
            raise TaskNotFoundException(task_id)
        return task

    def get_all_tasks(self, status: Optional[str] = None, limit: int = 100) -> List[Task]:
        """Get all tasks with optional filtering."""
        try:
            return self.db_manager.get_all_tasks(status=status, limit=limit)
        except Exception as e:
            raise DatabaseException(f"Failed to retrieve tasks: {str(e)}")

    def get_database_manager(self) -> DatabaseManager:
        """Get the underlying database manager."""
        return self.db_manager


# Global database service instance
db_service = DatabaseService()
