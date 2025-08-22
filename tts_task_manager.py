import hashlib
import json
import queue
import sqlite3
import threading
import time
from datetime import datetime
from typing import Optional, Dict, Any, List

from manager_sql import SQL_CREATE_TASKS_TABLE, SQL_CREATE_INDEX_TASK_ID, SQL_CREATE_INDEX_TEXT_HASH, \
    SQL_CREATE_INDEX_STATUS, SQL_CHECK_TASK_EXISTS, SQL_SELECT_COMPLETED_BY_HASH, \
    SQL_SELECT_TASK_BY_ID, SQL_SELECT_ALL_TASKS, SQL_SELECT_TASKS_BY_STATUS, SQL_SELECT_TASKS_BY_HASH, \
    SQL_UPDATE_TASK_BASE, SQL_STATS_STATUS_COUNTS, SQL_STATS_TOTAL_TASKS, SQL_STATS_AVG_FILE_SIZE, \
    SQL_STATS_DUPLICATE_HASHES, SQL_CLEANUP_FAILED_TASKS, SQL_SELECT_EXISTING_BY_HASH, SQL_INSERT_TASK


class TTSTaskManager:
    def __init__(self, db_path: str = "tts_tasks.db", tts_service=None):
        self.db_path = db_path
        self.tts_service = tts_service
        self.is_running = False
        self.monitor_thread = None

        # Initialize database
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Create tasks table
            cursor.execute(SQL_CREATE_TASKS_TABLE)

            # Create indexes for faster lookups
            cursor.execute(SQL_CREATE_INDEX_TASK_ID)
            cursor.execute(SQL_CREATE_INDEX_TEXT_HASH)
            cursor.execute(SQL_CREATE_INDEX_STATUS)

            conn.commit()

    def _calculate_text_hash(self, text: str) -> str:
        """Calculate MD5 hash of text for deduplication"""
        return hashlib.md5(text.encode()).hexdigest()

    def _datetime_to_string(self, dt: datetime) -> str:
        """Convert datetime to ISO format string for SQLite storage"""
        return dt.isoformat()

    def _get_existing_task_by_hash(self, text_hash: str) -> Optional[Dict]:
        """Get any existing task by text hash (any status except failed)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(SQL_SELECT_EXISTING_BY_HASH, (text_hash,))
            row = cursor.fetchone()
            return dict(row) if row else None

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
            status = existing_task['status']
            task_id = existing_task['task_id']

            if status == 'completed':
                print(f"Task with same text already completed (ID: {task_id})")
                return task_id
            elif status in ['queued', 'processing']:
                print(f"Task with same text already {status} (ID: {task_id})")
                return task_id

        # No existing task found, create new one
        task_id = self.tts_service.submit_request(text, custom_filename)
        if not task_id:
            return None

        # Insert initial task record into database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(SQL_INSERT_TASK, (
                task_id,
                text,
                text_hash,
                'queued',
                custom_filename,
                self._datetime_to_string(datetime.now())
            ))
            conn.commit()

        print(f"Created new task: {task_id}")
        return task_id

    def _task_exists(self, task_id: str) -> bool:
        """Check if task already exists in database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(SQL_CHECK_TASK_EXISTS, (task_id,))
            return cursor.fetchone() is not None

    def _get_completed_task_by_hash(self, text_hash: str) -> Optional[Dict]:
        """Get completed task by text hash for deduplication"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(SQL_SELECT_COMPLETED_BY_HASH, (text_hash,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get current status of a task"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(SQL_SELECT_TASK_BY_ID, (task_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_tasks(self, status: Optional[str] = None) -> List[Dict]:
        """Get all tasks, optionally filtered by status"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if status:
                cursor.execute(SQL_SELECT_TASKS_BY_STATUS, (status,))
            else:
                cursor.execute(SQL_SELECT_ALL_TASKS)

            return [dict(row) for row in cursor.fetchall()]

    def get_tasks_by_text_hash(self, text_hash: str) -> List[Dict]:
        """Get all tasks with the same text hash"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(SQL_SELECT_TASKS_BY_HASH, (text_hash,))
            return [dict(row) for row in cursor.fetchall()]

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
        task_id = message.get('request_id')
        status = message.get('status')
        output_file_path = message.get('output_file_path')
        metadata = message.get('metadata', {})

        if not task_id:
            return

        print(f"Updating task {task_id} status to {status}")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Prepare update data based on status
            update_data = {
                'status': status,
                'output_file_path': output_file_path,
                'metadata': json.dumps(metadata) if metadata else None
            }

            if status == 'processing':
                update_data['started_at'] = metadata.get('started_at', self._datetime_to_string(datetime.now()))
                update_data['device'] = metadata.get('device')

            elif status == 'completed':
                update_data['completed_at'] = metadata.get('completed_at', self._datetime_to_string(datetime.now()))
                update_data['file_size'] = metadata.get('file_size')
                update_data['sampling_rate'] = metadata.get('sampling_rate')
                update_data['device'] = metadata.get('device')

            elif status == 'failed':
                update_data['failed_at'] = metadata.get('failed_at', self._datetime_to_string(datetime.now()))
                update_data['error_message'] = metadata.get('error')
                update_data['device'] = metadata.get('device')

            # Build dynamic UPDATE query using the base template
            set_clauses = []
            values = []
            for key, value in update_data.items():
                if value is not None:
                    set_clauses.append(f"{key} = ?")
                    values.append(value)

            if set_clauses:
                values.append(task_id)
                query = SQL_UPDATE_TASK_BASE.format(columns=', '.join(set_clauses))
                cursor.execute(query, values)
                conn.commit()

    def get_statistics(self) -> Dict[str, Any]:
        """Get task statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get status counts
            cursor.execute(SQL_STATS_STATUS_COUNTS)
            status_counts = dict(cursor.fetchall())

            # Get total tasks
            cursor.execute(SQL_STATS_TOTAL_TASKS)
            total_tasks = cursor.fetchone()[0]

            # Get average file size for completed tasks
            cursor.execute(SQL_STATS_AVG_FILE_SIZE)
            avg_file_size = cursor.fetchone()[0]

            # Get duplicate text hashes
            cursor.execute(SQL_STATS_DUPLICATE_HASHES)
            duplicates = cursor.fetchall()

            return {
                'total_tasks': total_tasks,
                'status_counts': status_counts,
                'average_file_size': avg_file_size,
                'duplicate_texts': len(duplicates),
                'duplicate_details': duplicates
            }

    def cleanup_failed_tasks(self) -> int:
        """Remove failed tasks older than specified days"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(SQL_CLEANUP_FAILED_TASKS)
            deleted_count = cursor.rowcount
            conn.commit()

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
                print(f"Task {task_id}: {status['status']} - {status.get('output_file_path', 'N/A')}")

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

            if user_input.lower() == 'quit':
                break
            elif user_input.lower() == 'stats':
                stats = task_manager.get_statistics()
                for key, value in stats.items():
                    print(f"  {key}: {value}")
            elif user_input.lower().startswith('submit '):
                text = user_input[7:].strip()
                if text:
                    task_id = task_manager.submit_task(text)
                    print(f"Submitted task: {task_id}")
            elif user_input.lower().startswith('status '):
                task_id = user_input[7:].strip()
                status = task_manager.get_task_status(task_id)
                if status:
                    print(f"Task {task_id}:")
                    for key, value in status.items():
                        print(f"  {key}: {value}")
                else:
                    print(f"Task {task_id} not found")
            elif user_input.lower().startswith('list'):
                parts = user_input.split()
                status_filter = parts[1] if len(parts) > 1 else None
                tasks = task_manager.get_all_tasks(status_filter)
                print(f"Found {len(tasks)} tasks:")
                for task in tasks[:10]:  # Show only first 10
                    print(f"  {task['task_id']}: {task['status']} - {task['original_text'][:50]}...")
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
