"""Tests for DatabaseService."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from app.services.database import DatabaseService
from app.core.exceptions import TaskNotFoundException, DatabaseException
from app.models.database import Task


class TestDatabaseService:
    """Test cases for DatabaseService."""

    @pytest.fixture
    def database_service(self):
        """Create a database service instance for testing."""
        return DatabaseService()

    def test_init(self):
        """Test service initialization."""
        service = DatabaseService()
        assert service.db_manager is not None

    def test_get_task_by_id_success(self, database_service, db_manager):
        """Test successful task retrieval by ID."""
        # Create a task first
        with db_manager.get_session() as session:
            task = Task(
                task_id="test_task_123",
                original_text="Test text",
                text_hash="hash123",
                status="queued"
            )
            session.add(task)
            session.commit()
            session.refresh(task)
        
        # Get task by ID
        retrieved_task = database_service.get_task_by_id("test_task_123")
        
        assert retrieved_task is not None
        assert retrieved_task.task_id == "test_task_123"
        assert retrieved_task.original_text == "Test text"

    def test_get_task_by_id_not_found(self, database_service):
        """Test task retrieval with non-existent ID."""
        with pytest.raises(TaskNotFoundException) as exc_info:
            database_service.get_task_by_id("non_existent")
        
        assert "Task with ID 'non_existent' not found" in str(exc_info.value)

    def test_get_all_tasks_success(self, database_service, db_manager):
        """Test successful retrieval of all tasks."""
        # Create some tasks
        with db_manager.get_session() as session:
            for i in range(3):
                task = Task(
                    task_id=f"task_{i}",
                    original_text=f"Text {i}",
                    text_hash=f"hash{i}",
                    status="queued"
                )
                session.add(task)
            session.commit()
        
        # Get all tasks
        tasks = database_service.get_all_tasks()
        
        assert len(tasks) == 3
        assert all(isinstance(task, Task) for task in tasks)

    def test_get_all_tasks_with_status_filter(self, database_service, db_manager):
        """Test task retrieval with status filter."""
        # Create tasks with different statuses
        with db_manager.get_session() as session:
            for i in range(3):
                status = "queued" if i < 2 else "completed"
                task = Task(
                    task_id=f"task_{i}",
                    original_text=f"Text {i}",
                    text_hash=f"hash{i}",
                    status=status
                )
                session.add(task)
            session.commit()
        
        # Get tasks with status filter
        queued_tasks = database_service.get_all_tasks(status="queued")
        completed_tasks = database_service.get_all_tasks(status="completed")
        
        assert len(queued_tasks) == 2
        assert len(completed_tasks) == 1
        assert all(task.status == "queued" for task in queued_tasks)
        assert all(task.status == "completed" for task in completed_tasks)

    def test_get_all_tasks_with_limit(self, database_service, db_manager):
        """Test task retrieval with limit."""
        # Create many tasks
        with db_manager.get_session() as session:
            for i in range(10):
                task = Task(
                    task_id=f"task_{i}",
                    original_text=f"Text {i}",
                    text_hash=f"hash{i}",
                    status="queued"
                )
                session.add(task)
            session.commit()
        
        # Get tasks with limit
        tasks = database_service.get_all_tasks(limit=5)
        
        assert len(tasks) == 5

    def test_get_all_tasks_database_error(self, database_service):
        """Test task retrieval when database raises error."""
        # Mock database manager to raise exception
        mock_db_manager = Mock()
        mock_db_manager.get_all_tasks.side_effect = Exception("Database connection failed")
        database_service.db_manager = mock_db_manager
        
        with pytest.raises(DatabaseException) as exc_info:
            database_service.get_all_tasks()
        
        assert "Failed to retrieve tasks" in str(exc_info.value)

    def test_get_database_manager(self, database_service):
        """Test getting the underlying database manager."""
        db_manager = database_service.get_database_manager()
        
        assert db_manager is not None
        assert db_manager == database_service.db_manager

    def test_get_task_by_id_database_error(self, database_service):
        """Test task retrieval when database raises error."""
        # Mock database manager to raise exception
        mock_db_manager = Mock()
        mock_db_manager.get_task_by_id.side_effect = Exception("Database connection failed")
        database_service.db_manager = mock_db_manager
        
        with pytest.raises(DatabaseException) as exc_info:
            database_service.get_task_by_id("test_id")
        
        # Should raise the original exception, not wrap it
        assert "Database connection failed" in str(exc_info.value)

    def test_get_all_tasks_default_parameters(self, database_service, db_manager):
        """Test task retrieval with default parameters."""
        # Create a task
        with db_manager.get_session() as session:
            task = Task(
                task_id="default_task",
                original_text="Default text",
                text_hash="default_hash",
                status="queued"
            )
            session.add(task)
            session.commit()
        
        # Get tasks with default parameters
        tasks = database_service.get_all_tasks()
        
        assert len(tasks) == 1
        assert tasks[0].task_id == "default_task"

    def test_get_all_tasks_empty_database(self, database_service):
        """Test task retrieval from empty database."""
        tasks = database_service.get_all_tasks()
        
        assert len(tasks) == 0

    def test_get_all_tasks_invalid_status(self, database_service, db_manager):
        """Test task retrieval with invalid status filter."""
        # Create a task
        with db_manager.get_session() as session:
            task = Task(
                task_id="test_task",
                original_text="Test text",
                text_hash="test_hash",
                status="queued"
            )
            session.add(task)
            session.commit()
        
        # Get tasks with invalid status
        tasks = database_service.get_all_tasks(status="invalid_status")
        
        assert len(tasks) == 0  # Should return empty list for invalid status

    def test_get_all_tasks_limit_validation(self, database_service):
        """Test task retrieval with invalid limit values."""
        # Test with negative limit
        with pytest.raises(ValueError):
            database_service.get_all_tasks(limit=-1)
        
        # Test with zero limit
        with pytest.raises(ValueError):
            database_service.get_all_tasks(limit=0)

    def test_get_all_tasks_status_validation(self, database_service):
        """Test task retrieval with invalid status values."""
        # Test with None status
        tasks = database_service.get_all_tasks(status=None)
        assert isinstance(tasks, list)
        
        # Test with empty string status
        tasks = database_service.get_all_tasks(status="")
        assert isinstance(tasks, list)

    def test_error_handling_integration(self, database_service):
        """Test comprehensive error handling."""
        # Test various error scenarios
        error_scenarios = [
            ("Connection timeout", "Database connection timeout"),
            ("Permission denied", "Database permission denied"),
            ("Table not found", "Database table not found"),
        ]
        
        for error_type, error_message in error_scenarios:
            mock_db_manager = Mock()
            mock_db_manager.get_all_tasks.side_effect = Exception(error_message)
            database_service.db_manager = mock_db_manager
            
            with pytest.raises(DatabaseException) as exc_info:
                database_service.get_all_tasks()
            
            assert error_message in str(exc_info.value)

    def test_session_management(self, database_service, db_manager):
        """Test that sessions are properly managed."""
        # Create a task
        with db_manager.get_session() as session:
            task = Task(
                task_id="session_test_task",
                original_text="Session test text",
                text_hash="session_hash",
                status="queued"
            )
            session.add(task)
            session.commit()
            session.refresh(task)
        
        # Verify task was created and can be retrieved
        retrieved_task = database_service.get_task_by_id("session_test_task")
        assert retrieved_task is not None
        assert retrieved_task.original_text == "Session test text"

    def test_transaction_rollback_on_error(self, database_service, db_manager):
        """Test that transactions are rolled back on errors."""
        # This test verifies that database errors don't leave partial transactions
        try:
            with db_manager.get_session() as session:
                # Create a valid task
                task = Task(
                    task_id="rollback_test_task",
                    original_text="Rollback test text",
                    text_hash="rollback_hash",
                    status="queued"
                )
                session.add(task)
                
                # Try to create an invalid task (this should fail)
                invalid_task = Task(
                    task_id="rollback_test_task",  # Duplicate ID should cause error
                    original_text="Invalid task",
                    text_hash="invalid_hash",
                    status="queued"
                )
                session.add(invalid_task)
                session.commit()  # This should fail
        except Exception:
            pass  # Expected to fail
        
        # Verify that no tasks were created due to rollback
        with db_manager.get_session() as session:
            tasks = session.query(Task).filter(Task.task_id == "rollback_test_task").all()
            assert len(tasks) == 0
