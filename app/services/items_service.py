"""Items service for managing dictation items."""

import os
import threading
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import and_

from app.core.config import settings
from app.core.logging import get_logger
from app.models.database import DatabaseManager, Item

# Setup logger for this module
logger = get_logger(__name__)


class ItemsService:
    """Service for managing dictation items."""

    def __init__(self, db_manager: DatabaseManager, task_manager=None):
        self.db_manager = db_manager
        self.task_manager = task_manager

    def _calculate_difficulty_from_text(self, text: str) -> int:
        """Calculate difficulty level based on text length rules."""
        # Count words and letters
        words = len(text.split())
        letters = len(text.replace(" ", ""))
        
        # Apply difficulty rules
        if words <= 6 or letters <= 50:
            return 1
        elif 7 <= words <= 9 or 51 <= letters <= 80:
            return 2
        elif 10 <= words <= 12 or 81 <= letters <= 110:
            return 3
        elif 13 <= words <= 15 or 111 <= letters <= 140:
            return 4
        else:  # words >= 16 or letters >= 141
            return 5

    def _submit_tts_job_background(self, item_id: int, text: str, custom_filename: str):
        """Submit TTS job in background thread."""
        try:
            if self.task_manager:
                task_id = self.task_manager.submit_task_for_item(item_id, text, custom_filename)
                
                if not task_id:
                    # Mark TTS as failed if we couldn't submit
                    with self.db_manager.get_session() as session:
                        item = session.query(Item).filter(Item.id == item_id).first()
                        if item:
                            item.tts_status = "failed"
                            session.commit()
                            logger.warning(f"Failed to submit TTS job for item {item_id}")
                
                logger.info(f"TTS job submitted in background for item {item_id}: {task_id}")
            else:
                logger.warning(f"No task manager available for item {item_id}")
                
        except Exception as e:
            logger.error(f"Error submitting TTS job in background for item {item_id}: {e}")
            # Mark TTS as failed
            try:
                with self.db_manager.get_session() as session:
                    item = session.query(Item).filter(Item.id == item_id).first()
                    if item:
                        item.tts_status = "failed"
                        session.commit()
            except Exception as db_error:
                logger.error(f"Failed to update TTS status to failed for item {item_id}: {db_error}")

    def _submit_bulk_tts_jobs_background(self, items_data: List[Dict[str, Any]]):
        """Submit TTS jobs for multiple items in a single background thread."""
        try:
            if not self.task_manager:
                logger.warning("No task manager available for bulk TTS job submission")
                return

            for item_data in items_data:
                try:
                    item_id = item_data["id"]
                    text = item_data["text"]
                    custom_filename = f"item_{item_id}"
                    task_id = self.task_manager.submit_task_for_item(item_id, text, custom_filename)
                    
                    if not task_id:
                        # Mark TTS as failed if we couldn't submit
                        with self.db_manager.get_session() as session:
                            item = session.query(Item).filter(Item.id == item_id).first()
                            if item:
                                item.tts_status = "failed"
                                session.commit()
                                logger.warning(f"Failed to submit TTS job for item {item_id}")
                    
                    logger.info(f"TTS job submitted in background for item {item_id}: {task_id}")
                    
                except Exception as e:
                    logger.error(f"Error submitting TTS job for item {item_data.get('id', 'unknown')}: {e}")
                    # Mark TTS as failed
                    try:
                        item_id = item_data.get("id")
                        if item_id:
                            with self.db_manager.get_session() as session:
                                item = session.query(Item).filter(Item.id == item_id).first()
                                if item:
                                    item.tts_status = "failed"
                                    session.commit()
                    except Exception as db_error:
                        logger.error(f"Failed to update TTS status to failed for item {item_data.get('id', 'unknown')}: {db_error}")
                        
        except Exception as e:
            logger.error(f"Error in bulk TTS job submission: {e}")

    def create_item(
            self,
            locale: str,
            text: str,
            difficulty: Optional[int] = None,
            tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a new dictation item and enqueue TTS job in background."""
        # Auto-calculate difficulty if not provided
        if difficulty is None:
            difficulty = self._calculate_difficulty_from_text(text)
        
        with self.db_manager.get_session() as session:
            # Create item with pending TTS status
            item = Item(
                locale=locale,
                text=text,
                difficulty=difficulty,
                tags_json=None,
                tts_status="pending",
            )

            if tags:
                item.tags = tags

            session.add(item)
            session.commit()
            session.refresh(item)

            # Submit TTS job in background thread
            if self.task_manager:
                custom_filename = f"item_{item.id}"
                background_thread = threading.Thread(
                    target=self._submit_tts_job_background,
                    args=(item.id, text, custom_filename),
                    daemon=True
                )
                background_thread.start()
                logger.info(f"Started background TTS job for item {item.id}")

            # Return clean data structure to avoid session binding issues
            return self._item_to_dict(item)

    def bulk_create_items(
            self,
            items_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create multiple dictation items and enqueue TTS jobs in background."""
        created_items = []
        failed_items = []
        
        with self.db_manager.get_session() as session:
            for item_data in items_data:
                try:
                    # Create item with pending TTS status
                    item = Item(
                        locale=item_data["locale"],
                        text=item_data["text"],
                        difficulty=item_data.get("difficulty"),
                        tags_json=None,
                        tts_status="pending",
                    )

                    # Auto-calculate difficulty if not provided
                    if item.difficulty is None:
                        item.difficulty = self._calculate_difficulty_from_text(item_data["text"])

                    if item_data.get("tags"):
                        item.tags = item_data["tags"]

                    session.add(item)
                    session.flush()  # Get the ID without committing
                    session.refresh(item)

                    created_items.append(item)

                except Exception as e:
                    logger.error(f"Failed to create item: {e}")
                    failed_items.append({
                        "data": item_data,
                        "error": str(e)
                    })

            # Commit all successful creations
            session.commit()
            
            # Submit TTS jobs in a single background thread for all created items
            if self.task_manager and created_items:
                # Prepare data for background thread (avoid session binding issues)
                background_items_data = [
                    {
                        "id": item.id,
                        "text": item.text,
                        "locale": item.locale
                    }
                    for item in created_items
                ]
                
                background_thread = threading.Thread(
                    target=self._submit_bulk_tts_jobs_background,
                    args=(background_items_data,),
                    daemon=True
                )
                background_thread.start()
                logger.info(f"Started background TTS job processing for {len(created_items)} items")
            
            # Convert items to clean data structures to avoid session binding issues
            created_items_data = [self._item_to_dict(item) for item in created_items]
            
            return {
                "created_items": created_items_data,
                "failed_items": failed_items
            }

    def get_item(self, item_id: int) -> Optional[Item]:
        """Get an item by ID."""
        with self.db_manager.get_session() as session:
            return session.query(Item).filter(Item.id == item_id).first()

    def delete_item(self, item_id: int) -> bool:
        """Delete an item and its associated audio file."""
        with self.db_manager.get_session() as session:
            item = session.query(Item).filter(Item.id == item_id).first()
            if not item:
                return False

            # Delete associated audio file if it exists
            # Check if audio file exists using predictable naming convention
            audio_filename = f"item_{item_id}.wav"
            file_path = os.path.join(settings.audio_dir, audio_filename)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    logger.warning(f"Failed to delete audio file for item {item_id}: {e}")

            # Delete the item (cascades to attempts and updates task)
            session.delete(item)
            session.commit()
            return True

    def list_items(
            self,
            locale: Optional[str] = None,
            tags: Optional[List[str]] = None,
            difficulty: Optional[str] = None,  # Single value or "min..max"
            practiced: Optional[bool] = None,
            sort: str = "created_at.desc",
            page: int = 1,
            per_page: int = 20,
    ) -> Dict[str, Any]:
        """List items with filtering and pagination."""
        with self.db_manager.get_session() as session:
            # Start with base query
            query = session.query(Item)

            # Apply filters
            if locale:
                query = query.filter(Item.locale == locale)

            if tags:
                # Items must have all specified tags
                for tag in tags:
                    query = query.filter(Item.tags_json.like(f'%"{tag}"%'))

            if difficulty:
                if ".." in difficulty:
                    # Range query: "1..5"
                    try:
                        min_diff, max_diff = map(int, difficulty.split(".."))
                        query = query.filter(
                            and_(
                                Item.difficulty >= min_diff,
                                Item.difficulty <= max_diff
                            )
                        )
                    except ValueError:
                        pass  # Invalid range format, ignore
                else:
                    # Single value
                    try:
                        diff_value = int(difficulty)
                        query = query.filter(Item.difficulty == diff_value)
                    except ValueError:
                        pass  # Invalid number, ignore

            if practiced is not None:
                if practiced:
                    # Items with at least one attempt
                    query = query.filter(Item.attempts.any())
                else:
                    # Items with no attempts
                    query = query.filter(~Item.attempts.any())

            # Apply sorting
            if sort == "created_at.asc":
                query = query.order_by(Item.created_at.asc())
            elif sort == "created_at.desc":
                query = query.order_by(Item.created_at.desc())
            elif sort == "difficulty.asc":
                query = query.order_by(Item.difficulty.asc().nulls_last())
            elif sort == "difficulty.desc":
                query = query.order_by(Item.difficulty.desc().nulls_last())
            else:
                # Default sort
                query = query.order_by(Item.created_at.desc())

            # Get total count before pagination
            total = query.count()

            # Apply pagination
            offset = (page - 1) * per_page
            items = query.offset(offset).limit(per_page).all()

            # Build response
            return {
                "items": [self._item_to_dict(item) for item in items],
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": (total + per_page - 1) // per_page,
            }

    def update_item_tts_status(
            self,
            item_id: int,
            status: str
    ) -> bool:
        """Update the TTS status for an item."""
        with self.db_manager.get_session() as session:
            item = session.query(Item).filter(Item.id == item_id).first()
            if not item:
                return False

            item.tts_status = status
            item.updated_at = datetime.now()

            session.commit()
            return True

    def update_item_tags(
            self,
            item_id: int,
            operation: str,
            **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Update tags for an item based on the specified operation."""
        with self.db_manager.get_session() as session:
            item = session.query(Item).filter(Item.id == item_id).first()
            if not item:
                return None

            previous_tags = item.tags.copy() if item.tags else []
            current_tags = previous_tags.copy()
            message = ""

            if operation == "replace":
                # Replace all tags
                new_tags = kwargs.get("tags", [])
                current_tags = new_tags
                message = f"Replaced all tags with: {', '.join(new_tags) if new_tags else 'none'}"

            elif operation == "add":
                # Add new tags
                add_tags = kwargs.get("add_tags", [])
                for tag in add_tags:
                    if tag not in current_tags:
                        current_tags.append(tag)
                message = f"Added tags: {', '.join(add_tags)}"

            elif operation == "remove":
                # Remove specific tags
                remove_tags = kwargs.get("remove_tags", [])
                for tag in remove_tags:
                    if tag in current_tags:
                        current_tags.remove(tag)
                message = f"Removed tags: {', '.join(remove_tags)}"

            elif operation == "modify":
                # Modify specific tags
                tag_modifications = kwargs.get("tag_modifications", [])
                for mod in tag_modifications:
                    old_tag = mod.get("old")
                    new_tag = mod.get("new")
                    if old_tag in current_tags:
                        index = current_tags.index(old_tag)
                        current_tags[index] = new_tag
                message = f"Modified {len(tag_modifications)} tag(s)"

            # Update the item
            item.tags = current_tags
            item.updated_at = datetime.now()
            session.commit()

            return {
                "item_id": item.id,
                "operation": operation,
                "previous_tags": previous_tags,
                "current_tags": current_tags,
                "updated_at": item.updated_at,
                "message": message
            }

    def update_item_difficulty(
            self,
            item_id: int,
            difficulty: int
    ) -> Optional[Dict[str, Any]]:
        """Update the difficulty level for an item."""
        with self.db_manager.get_session() as session:
            item = session.query(Item).filter(Item.id == item_id).first()
            if not item:
                return None

            previous_difficulty = item.difficulty
            
            # Update the difficulty
            item.difficulty = difficulty
            item.updated_at = datetime.now()
            session.commit()

            # Create message based on whether difficulty was previously set
            if previous_difficulty is None:
                message = f"Set difficulty to {difficulty}"
            else:
                message = f"Updated difficulty from {previous_difficulty} to {difficulty}"

            return {
                "item_id": item.id,
                "previous_difficulty": previous_difficulty,
                "current_difficulty": difficulty,
                "updated_at": item.updated_at,
                "message": message
            }

    def get_items_tts_status(self, item_ids: List[int]) -> Dict[str, Any]:
        """Get TTS status for multiple items."""
        with self.db_manager.get_session() as session:
            items = session.query(Item).filter(Item.id.in_(item_ids)).all()
            
            status_info = {}
            for item in items:
                status_info[item.id] = {
                    "id": item.id,
                    "text": item.text[:100] + "..." if len(item.text) > 100 else item.text,
                    "tts_status": item.tts_status,
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                    "updated_at": item.updated_at.isoformat() if item.updated_at else None,
                }
            
            return status_info

    def _item_to_dict(self, item: Item) -> Dict[str, Any]:
        """Convert Item model to dictionary."""
        return {
            "id": item.id,
            "locale": item.locale,
            "text": item.text,
            "difficulty": item.difficulty,
            "tags": item.tags,
            "tts_status": item.tts_status,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
            "practiced": item.has_attempts,
        }
