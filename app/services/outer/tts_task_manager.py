import hashlib
import json
import queue
import threading
import time
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func

from app.core.config import settings
from app.models.database import DatabaseManager, Task


class TTSTaskManager:
    def __init__(self, database_url: str = settings.database_url, tts_service=None):
        self.db_manager = DatabaseManager(database_url)
        self.tts_service = tts_service
        self.is_running = False
        self.monitor_thread = None

    def _calculate_text_hash(self, text: str) -> str:
        """Calculate MD5 hash of text for deduplication"""
        return hashlib.md5(text.encode()).hexdigest()

    def _get_existing_task_by_hash(self, text_hash: str) -> Optional[Task]:
        """Get any existing task by text hash (any status except failed)"""
        with self.db_manager.get_session() as session:
            return (
                session.query(Task)
                .filter(and_(Task.text_hash == text_hash, Task.status != "failed"))
                .first()
            )

    def submit_task(self, text: str, custom_filename: Optional[str] = None) -> Optional[str]:
        """Submit a new TTS task and store it in database"""
        if not text.strip():
            print("Error: Empty text provided")
            return None

        if not self.tts_service:
            print("Error: TTS service not available")
            return None

        text_hash = self._calculate_text_hash(text)

        # Check for existing task with same text hash (any status except failed)
        existing_task = self._get_existing_task_by_hash(text_hash)
        if existing_task:
            status = existing_task.status
            task_id = existing_task.task_id

            if status in ["completed", "done"]:
                print(f"Task with same text already completed (ID: {task_id})")
                return task_id
            elif status in ["queued", "processing"]:
                print(f"Task with same text already {status} (ID: {task_id})")
                return task_id

        # No existing task found, create new one
        task_id = self.tts_service.submit_request(text, custom_filename)
        if not task_id:
            return None

        # Insert initial task record into database
        with self.db_manager.get_session() as session:
            new_task = Task(
                task_id=task_id,
                original_text=text,
                text_hash=text_hash,
                status="queued",
                custom_filename=custom_filename,
                created_at=datetime.now(UTC),
                submitted_at=datetime.now(UTC),
            )
            session.add(new_task)
            session.commit()

        print(f"Created new task: {task_id}")
        return task_id

    def _task_exists(self, task_id: str) -> bool:
        """Check if task already exists in database"""
        with self.db_manager.get_session() as session:
            return session.query(Task).filter(Task.task_id == task_id).first() is not None

    def _get_completed_task_by_hash(self, text_hash: str) -> Optional[Task]:
        """Get completed task by text hash for deduplication"""
        with self.db_manager.get_session() as session:
            return (
                session.query(Task)
                .filter(and_(Task.text_hash == text_hash, Task.status == "completed"))
                .first()
            )

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get current status of a task"""
        with self.db_manager.get_session() as session:
            task = session.query(Task).filter(Task.task_id == task_id).first()
            if task:
                return {
                    "id": task.id,
                    "task_id": task.task_id,
                    "original_text": task.original_text,
                    "text_hash": task.text_hash,
                    "status": task.status,
                    "output_file_path": task.output_file_path,
                    "custom_filename": task.custom_filename,
                    "created_at": task.created_at.isoformat() if task.created_at else None,
                    "submitted_at": task.submitted_at.isoformat() if task.submitted_at else None,
                    "started_at": task.started_at.isoformat() if task.started_at else None,
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                    "failed_at": task.failed_at.isoformat() if task.failed_at else None,
                    "error_message": task.error_message,
                    "file_size": task.file_size,
                    "sampling_rate": task.sampling_rate,
                    "device": task.device,
                    "metadata": task.metadata_dict,
                    "duration": task.duration,
                }
            return None

    def get_all_tasks(self, status: Optional[str] = None) -> List[Dict]:
        """Get all tasks, optionally filtered by status"""
        with self.db_manager.get_session() as session:
            query = session.query(Task)
            if status:
                query = query.filter(Task.status == status)

            tasks = query.order_by(Task.created_at.desc()).all()

            return [
                {
                    "id": task.id,
                    "task_id": task.task_id,
                    "original_text": task.original_text,
                    "text_hash": task.text_hash,
                    "status": task.status,
                    "output_file_path": task.output_file_path,
                    "custom_filename": task.custom_filename,
                    "created_at": task.created_at.isoformat() if task.created_at else None,
                    "submitted_at": task.submitted_at.isoformat() if task.submitted_at else None,
                    "started_at": task.started_at.isoformat() if task.started_at else None,
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                    "failed_at": task.failed_at.isoformat() if task.failed_at else None,
                    "error_message": task.error_message,
                    "file_size": task.file_size,
                    "sampling_rate": task.sampling_rate,
                    "device": task.device,
                    "metadata": task.metadata_dict,
                    "duration": task.duration,
                }
                for task in tasks
            ]

    def get_tasks_by_text_hash(self, text_hash: str) -> List[Dict]:
        """Get all tasks with the same text hash"""
        with self.db_manager.get_session() as session:
            tasks = session.query(Task).filter(Task.text_hash == text_hash).all()

            return [
                {
                    "id": task.id,
                    "task_id": task.task_id,
                    "original_text": task.original_text,
                    "text_hash": task.text_hash,
                    "status": task.status,
                    "output_file_path": task.output_file_path,
                    "custom_filename": task.custom_filename,
                    "created_at": task.created_at.isoformat() if task.created_at else None,
                    "submitted_at": task.submitted_at.isoformat() if task.submitted_at else None,
                    "started_at": task.started_at.isoformat() if task.started_at else None,
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                    "failed_at": task.failed_at.isoformat() if task.failed_at else None,
                    "error_message": task.error_message,
                    "file_size": task.file_size,
                    "sampling_rate": task.sampling_rate,
                    "device": task.device,
                    "metadata": task.metadata_dict,
                    "duration": task.duration,
                }
                for task in tasks
            ]

    def start_monitoring(self):
        """Start monitoring TTS service task queue"""
        if not self.is_running and self.tts_service:
            self.is_running = True
            self.monitor_thread = threading.Thread(target=self._monitor_task_queue, daemon=True)
            self.monitor_thread.start()
            print("Task monitoring started!")

    def stop_monitoring(self):
        """Stop monitoring task queue"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join()
        print("Task monitoring stopped!")

    def _monitor_task_queue(self):
        """Monitor TTS service task queue and update database"""
        task_queue = self.tts_service.get_task_queue()

        while self.is_running:
            try:
                # Get task message from queue with timeout
                task_message = task_queue.get(timeout=1)
                self._update_task_from_message(task_message)
                task_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error monitoring task queue: {e}")

    def _update_task_from_message(self, message: Dict[str, Any]):
        """Update task status based on task queue message"""
        task_id = message.get("request_id")
        status = message.get("status")
        output_file_path = message.get("output_file_path")
        metadata = message.get("metadata", {})

        if not task_id:
            return

        print(f"Updating task {task_id} status to {status}")

        with self.db_manager.get_session() as session:
            task = session.query(Task).filter(Task.task_id == task_id).first()

            if not task:
                print(f"Task {task_id} not found in database")
                return

            # Update basic fields
            task.status = status
            task.output_file_path = output_file_path
            task.task_metadata = json.dumps(metadata) if metadata else None

            # Update status-specific fields
            if status == "processing":
                if metadata.get("started_at"):
                    task.started_at = datetime.fromisoformat(metadata["started_at"])
                else:
                    task.started_at = datetime.now(UTC)
                task.device = metadata.get("device")

            elif status == "completed":
                if metadata.get("completed_at"):
                    task.completed_at = datetime.fromisoformat(metadata["completed_at"])
                else:
                    task.completed_at = datetime.now(UTC)
                task.file_size = metadata.get("file_size")
                task.sampling_rate = metadata.get("sampling_rate")
                task.device = metadata.get("device")

            elif status == "failed":
                if metadata.get("failed_at"):
                    task.failed_at = datetime.fromisoformat(metadata["failed_at"])
                else:
                    task.failed_at = datetime.now(UTC)
                task.error_message = metadata.get("error")
                task.device = metadata.get("device")

            session.commit()

    def get_statistics(self) -> Dict[str, Any]:
        """Get task statistics"""
        with self.db_manager.get_session() as session:
            # Get status counts
            status_counts = {}
            status_results = (
                session.query(Task.status, func.count(Task.id)).group_by(Task.status).all()
            )
            for status, count in status_results:
                status_counts[status] = count

            # Get total tasks
            total_tasks = session.query(func.count(Task.id)).scalar()

            # Get average file size for completed tasks
            avg_file_size = (
                session.query(func.avg(Task.file_size))
                .filter(and_(Task.status == "completed", Task.file_size.isnot(None)))
                .scalar()
            )

            # Get duplicate text hashes
            duplicate_results = (
                session.query(Task.text_hash, func.count(Task.id).label("count"))
                .group_by(Task.text_hash)
                .having(func.count(Task.id) > 1)
                .all()
            )

            return {
                "total_tasks": total_tasks or 0,
                "status_counts": status_counts,
                "average_file_size": float(avg_file_size) if avg_file_size else 0.0,
                "duplicate_texts": len(duplicate_results),
                "duplicate_details": [(hash_val, count) for hash_val, count in duplicate_results],
            }

    def cleanup_failed_tasks(self, days: int = 7) -> int:
        """Remove failed tasks older than specified days"""
        cutoff_date = datetime.now(UTC) - timedelta(days=days)

        with self.db_manager.get_session() as session:
            deleted_count = (
                session.query(Task)
                .filter(and_(Task.status == "failed", Task.failed_at < cutoff_date))
                .delete()
            )
            session.commit()

        print(f"Cleaned up {deleted_count} old failed tasks")
        return deleted_count


def main():
    """Example usage of TTSTaskManager with FBTTSService"""
    from tts_fb_service import FBTTSService

    # Initialize services
    print("=== TTS Task Manager Demo ===")
    tts_service = FBTTSService()
    task_manager = TTSTaskManager(tts_service=tts_service)

    # Start services
    tts_service.start_service()
    task_manager.start_monitoring()

    # Submit some test tasks
    print("\n=== Submitting Test Tasks ===")
    task1 = task_manager.submit_task("Hei, tämä on ensimmäinen testi!", "test1")
    task2 = task_manager.submit_task("Toinen testi suomen kielellä.", "test2")
    task3 = task_manager.submit_task("Hei, tämä on ensimmäinen testi!")  # Duplicate text

    # Wait for processing
    print("\nWaiting for tasks to process...")
    time.sleep(5)

    # Check task statuses
    print("\n=== Task Statuses ===")
    for task_id in [task1, task2, task3]:
        if task_id:
            status = task_manager.get_task_status(task_id)
            if status:
                print(
                    f"Task {task_id}: {status['status']} - {status.get('output_file_path', 'N/A')}"
                )

    # Show statistics
    print("\n=== Statistics ===")
    stats = task_manager.get_statistics()
    for key, value in stats.items():
        print(f"{key}: {value}")

    # Interactive mode
    print("\n=== Interactive Mode ===")
    print("Commands: 'submit <text>', 'status <task_id>', 'list [status]', 'stats', 'quit'")

    try:
        while True:
            user_input = input("\nCommand: ").strip()

            if user_input.lower() == "quit":
                break
            elif user_input.lower() == "stats":
                stats = task_manager.get_statistics()
                for key, value in stats.items():
                    print(f"  {key}: {value}")
            elif user_input.lower().startswith("submit "):
                text = user_input[7:].strip()
                if text:
                    task_id = task_manager.submit_task(text)
                    print(f"Submitted task: {task_id}")
            elif user_input.lower().startswith("status "):
                task_id = user_input[7:].strip()
                status = task_manager.get_task_status(task_id)
                if status:
                    print(f"Task {task_id}:")
                    for key, value in status.items():
                        print(f"  {key}: {value}")
                else:
                    print(f"Task {task_id} not found")
            elif user_input.lower().startswith("list"):
                parts = user_input.split()
                status_filter = parts[1] if len(parts) > 1 else None
                tasks = task_manager.get_all_tasks(status_filter)
                print(f"Found {len(tasks)} tasks:")
                for task in tasks[:10]:  # Show only first 10
                    print(
                        f"  {task['task_id']}: {task['status']} - {task['original_text'][:50]}..."
                    )
            else:
                print("Unknown command")

    except KeyboardInterrupt:
        print("\nShutting down...")

    # Cleanup
    task_manager.stop_monitoring()
    tts_service.stop_service()
    print("Services stopped. Goodbye!")


if __name__ == "__main__":
    main()
