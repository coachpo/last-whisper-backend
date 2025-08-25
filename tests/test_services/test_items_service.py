"""Tests for ItemsService."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, UTC

from app.services.items_service import ItemsService
from app.models.database import Item, Attempt


class TestItemsService:
    """Test cases for ItemsService."""

    @pytest.fixture
    def mock_task_manager(self):
        """Create a mock task manager."""
        mock_manager = Mock()
        mock_manager.submit_task_for_item.return_value = "test_task_123"
        return mock_manager

    @pytest.fixture
    def items_service(self, db_manager, mock_task_manager):
        """Create an items service instance for testing."""
        return ItemsService(db_manager, mock_task_manager)

    def test_init(self, db_manager, mock_task_manager):
        """Test service initialization."""
        service = ItemsService(db_manager, mock_task_manager)
        assert service.db_manager == db_manager
        assert service.task_manager == mock_task_manager

    def test_create_item_success(self, items_service, db_manager):
        """Test successful item creation."""
        item_data = {
            "locale": "fi",
            "text": "Hei, tämä on testi!",
            "difficulty": 3,
            "tags": ["test", "basic"]
        }
        
        item = items_service.create_item(**item_data)
        
        assert item is not None
        assert item.locale == "fi"
        assert item.text == "Hei, tämä on testi!"
        assert item.difficulty == 3
        assert item.tags == ["test", "basic"]
        assert item.tts_status == "pending"
        assert item.audio_url is None

    def test_create_item_without_tags(self, items_service, db_manager):
        """Test item creation without tags."""
        item = items_service.create_item(
            locale="en",
            text="English test",
            difficulty=5
        )
        
        assert item is not None
        assert item.tags == []
        assert item.tts_status == "pending"

    def test_create_item_with_none_tags(self, items_service, db_manager):
        """Test item creation with None tags."""
        item = items_service.create_item(
            locale="en",
            text="English test",
            difficulty=5,
            tags=None
        )
        
        assert item is not None
        assert item.tags == []
        assert item.tts_status == "pending"

    def test_create_item_enqueues_tts_job(self, items_service, db_manager, mock_task_manager):
        """Test that TTS job is enqueued when creating item."""
        item = items_service.create_item(
            locale="fi",
            text="Test text for TTS",
            difficulty=3
        )
        
        # Verify TTS job was submitted
        mock_task_manager.submit_task_for_item.assert_called_once_with(
            item.id, "Test text for TTS", f"item_{item.id}"
        )

    def test_create_item_tts_job_failure(self, items_service, db_manager, mock_task_manager):
        """Test item creation when TTS job fails."""
        mock_task_manager.submit_task_for_item.side_effect = Exception("TTS service error")
        
        item = items_service.create_item(
            locale="fi",
            text="Test text",
            difficulty=3
        )
        
        # Item should be created but TTS status should be failed
        assert item is not None
        assert item.tts_status == "failed"

    def test_get_item_success(self, items_service, db_manager):
        """Test successful item retrieval."""
        # Create an item first
        with db_manager.get_session() as session:
            item = Item(
                locale="fi",
                text="Test item",
                tts_status="ready"
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            
            item_id = item.id
        
        # Get item
        retrieved_item = items_service.get_item(item_id)
        
        assert retrieved_item is not None
        assert retrieved_item.id == item_id
        assert retrieved_item.text == "Test item"

    def test_get_item_not_found(self, items_service):
        """Test getting non-existent item."""
        item = items_service.get_item(999)
        assert item is None

    def test_delete_item_success(self, items_service, db_manager):
        """Test successful item deletion."""
        # Create an item first
        with db_manager.get_session() as session:
            item = Item(
                locale="fi",
                text="Item to delete",
                tts_status="ready",
                audio_url="/audio/test.wav"
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            
            item_id = item.id
        
        # Delete item
        success = items_service.delete_item(item_id)
        
        assert success is True
        
        # Verify item was deleted
        with db_manager.get_session() as session:
            deleted_item = session.query(Item).filter(Item.id == item_id).first()
            assert deleted_item is None

    def test_delete_item_not_found(self, items_service):
        """Test deleting non-existent item."""
        success = items_service.delete_item(999)
        assert success is False

    @patch('app.services.items_service.os.path.exists')
    @patch('app.services.items_service.os.remove')
    def test_delete_item_with_audio_file(self, mock_remove, mock_exists, items_service, db_manager):
        """Test item deletion with associated audio file."""
        mock_exists.return_value = True
        
        # Create an item with audio URL
        with db_manager.get_session() as session:
            item = Item(
                locale="fi",
                text="Item with audio",
                tts_status="ready",
                audio_url="/audio/test.wav"
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            
            item_id = item.id
        
        # Delete item
        success = items_service.delete_item(item_id)
        
        assert success is True
        mock_remove.assert_called_once()

    def test_delete_item_audio_file_not_found(self, items_service, db_manager):
        """Test item deletion when audio file doesn't exist."""
        # Create an item with audio URL
        with db_manager.get_session() as session:
            item = Item(
                locale="fi",
                text="Item with audio",
                tts_status="ready",
                audio_url="/audio/test.wav"
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            
            item_id = item.id
        
        # Delete item (should not fail even if audio file doesn't exist)
        success = items_service.delete_item(item_id)
        
        assert success is True

    def test_list_items_basic(self, items_service, db_manager):
        """Test basic item listing."""
        # Create some items
        with db_manager.get_session() as session:
            for i in range(3):
                item = Item(
                    locale="fi",
                    text=f"Item {i}",
                    tts_status="ready"
                )
                session.add(item)
            session.commit()
        
        # List items
        result = items_service.list_items()
        
        assert result["total"] == 3
        assert len(result["items"]) == 3
        assert result["page"] == 1
        assert result["per_page"] == 20
        assert result["total_pages"] == 1

    def test_list_items_with_locale_filter(self, items_service, db_manager):
        """Test item listing with locale filter."""
        # Create items with different locales
        with db_manager.get_session() as session:
            for i in range(2):
                item = Item(
                    locale="fi",
                    text=f"Finnish item {i}",
                    tts_status="ready"
                )
                session.add(item)
            
            item = Item(
                locale="en",
                text="English item",
                tts_status="ready"
            )
            session.add(item)
            session.commit()
        
        # Filter by Finnish locale
        result = items_service.list_items(locale="fi")
        assert result["total"] == 2
        assert all(item["locale"] == "fi" for item in result["items"])

    def test_list_items_with_tags_filter(self, items_service, db_manager):
        """Test item listing with tags filter."""
        # Create items with different tags
        with db_manager.get_session() as session:
            item1 = Item(
                locale="fi",
                text="Item with test tag",
                tts_status="ready"
            )
            item1.tags = ["test", "basic"]
            session.add(item1)
            
            item2 = Item(
                locale="fi",
                text="Item with advanced tag",
                tts_status="ready"
            )
            item2.tags = ["advanced", "complex"]
            session.add(item2)
            
            session.commit()
        
        # Filter by test tag
        result = items_service.list_items(tags=["test"])
        assert result["total"] == 1
        assert "test" in result["items"][0]["tags"]

    def test_list_items_with_difficulty_filter_single(self, items_service, db_manager):
        """Test item listing with single difficulty filter."""
        # Create items with different difficulties
        with db_manager.get_session() as session:
            for i in range(3):
                item = Item(
                    locale="fi",
                    text=f"Item {i}",
                    difficulty=i + 1,
                    tts_status="ready"
                )
                session.add(item)
            session.commit()
        
        # Filter by difficulty 2
        result = items_service.list_items(difficulty="2")
        assert result["total"] == 1
        assert result["items"][0]["difficulty"] == 2

    def test_list_items_with_difficulty_filter_range(self, items_service, db_manager):
        """Test item listing with difficulty range filter."""
        # Create items with different difficulties
        with db_manager.get_session() as session:
            for i in range(5):
                item = Item(
                    locale="fi",
                    text=f"Item {i}",
                    difficulty=i + 1,
                    tts_status="ready"
                )
                session.add(item)
            session.commit()
        
        # Filter by difficulty range 2-4
        result = items_service.list_items(difficulty="2..4")
        assert result["total"] == 3
        assert all(2 <= item["difficulty"] <= 4 for item in result["items"])

    def test_list_items_with_text_search(self, items_service, db_manager):
        """Test item listing with text search."""
        # Create items with different texts
        with db_manager.get_session() as session:
            item1 = Item(
                locale="fi",
                text="Hei, tämä on testi!",
                tts_status="ready"
            )
            session.add(item1)
            
            item2 = Item(
                locale="fi",
                text="Täysin eri teksti",
                tts_status="ready"
            )
            session.add(item2)
            
            session.commit()
        
        # Search for "testi"
        result = items_service.list_items(q="testi")
        assert result["total"] == 1
        assert "testi" in result["items"][0]["text"]

    def test_list_items_with_practiced_filter(self, items_service, db_manager):
        """Test item listing with practiced filter."""
        # Create items and attempts
        with db_manager.get_session() as session:
            item1 = Item(
                locale="fi",
                text="Practiced item",
                tts_status="ready"
            )
            session.add(item1)
            session.commit()
            session.refresh(item1)
            
            # Create attempt for item1
            attempt = Attempt(
                item_id=item1.id,
                text="User attempt",
                percentage=80,
                wer=0.2,
                words_ref=5,
                words_correct=4
            )
            session.add(attempt)
            
            item2 = Item(
                locale="fi",
                text="Unpracticed item",
                tts_status="ready"
            )
            session.add(item2)
            
            session.commit()
        
        # Filter by practiced items
        practiced_result = items_service.list_items(practiced=True)
        assert practiced_result["total"] == 1
        assert practiced_result["items"][0]["text"] == "Practiced item"
        
        # Filter by unpracticed items
        unpracticed_result = items_service.list_items(practiced=False)
        assert unpracticed_result["total"] == 1
        assert unpracticed_result["items"][0]["text"] == "Unpracticed item"

    def test_list_items_with_sorting(self, items_service, db_manager):
        """Test item listing with different sorting options."""
        # Create items with different creation times
        with db_manager.get_session() as session:
            for i in range(3):
                item = Item(
                    locale="fi",
                    text=f"Item {i}",
                    tts_status="ready"
                )
                session.add(item)
            session.commit()
        
        # Test different sort options
        sort_options = ["created_at.asc", "created_at.desc", "difficulty.asc", "difficulty.desc"]
        
        for sort in sort_options:
            result = items_service.list_items(sort=sort)
            assert result["total"] == 3
            assert len(result["items"]) == 3

    def test_list_items_with_pagination(self, items_service, db_manager):
        """Test item listing with pagination."""
        # Create many items
        with db_manager.get_session() as session:
            for i in range(25):
                item = Item(
                    locale="fi",
                    text=f"Item {i}",
                    tts_status="ready"
                )
                session.add(item)
            session.commit()
        
        # Test pagination
        result = items_service.list_items(page=2, per_page=10)
        
        assert result["total"] == 25
        assert result["page"] == 2
        assert result["per_page"] == 10
        assert result["total_pages"] == 3
        assert len(result["items"]) == 10

    def test_update_item_tts_status(self, items_service, db_manager):
        """Test updating item TTS status."""
        # Create an item
        with db_manager.get_session() as session:
            item = Item(
                locale="fi",
                text="Test item",
                tts_status="pending"
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            
            item_id = item.id
        
        # Update TTS status
        success = items_service.update_item_tts_status(
            item_id, "ready", "/audio/test.wav"
        )
        
        assert success is True
        
        # Verify update
        with db_manager.get_session() as session:
            updated_item = session.query(Item).filter(Item.id == item_id).first()
            assert updated_item.tts_status == "ready"
            assert updated_item.audio_url == "/audio/test.wav"

    def test_update_item_tts_status_not_found(self, items_service):
        """Test updating TTS status for non-existent item."""
        success = items_service.update_item_tts_status(999, "ready")
        assert success is False

    def test_build_audio_url(self, items_service):
        """Test building audio URL from filename."""
        filename = "test_audio.wav"
        url = items_service.build_audio_url(filename)
        
        assert "test_audio.wav" in url
        assert url.startswith("http")

    def test_item_to_dict(self, items_service, db_manager):
        """Test converting item to dictionary."""
        # Create an item
        with db_manager.get_session() as session:
            item = Item(
                locale="fi",
                text="Test item",
                difficulty=3,
                tts_status="ready",
                audio_url="/audio/test.wav"
            )
            item.tags = ["test", "basic"]
            session.add(item)
            session.commit()
            session.refresh(item)
        
        # Convert to dict
        item_dict = items_service._item_to_dict(item)
        
        assert item_dict["id"] == item.id
        assert item_dict["locale"] == "fi"
        assert item_dict["text"] == "Test item"
        assert item_dict["difficulty"] == 3
        assert item_dict["tags"] == ["test", "basic"]
        assert item_dict["tts_status"] == "ready"
        assert item_dict["audio_url"] == "/audio/test.wav"
        assert "created_at" in item_dict
        assert "updated_at" in item_dict
        assert "practiced" in item_dict

    def test_list_items_invalid_sort(self, items_service, db_manager):
        """Test item listing with invalid sort parameter."""
        # Create an item
        with db_manager.get_session() as session:
            item = Item(
                locale="fi",
                text="Test item",
                tts_status="ready"
            )
            session.add(item)
            session.commit()
        
        # Test with invalid sort
        result = items_service.list_items(sort="invalid_sort")
        
        # Should use default sort
        assert result["total"] == 1
        assert len(result["items"]) == 1

    def test_list_items_invalid_difficulty_range(self, items_service, db_manager):
        """Test item listing with invalid difficulty range."""
        # Create an item
        with db_manager.get_session() as session:
            item = Item(
                locale="fi",
                text="Test item",
                difficulty=3,
                tts_status="ready"
            )
            session.add(item)
            session.commit()
        
        # Test with invalid range format
        result = items_service.list_items(difficulty="invalid..range")
        
        # Should ignore invalid filter
        assert result["total"] == 1
        assert len(result["items"]) == 1

    def test_list_items_empty_database(self, items_service):
        """Test item listing from empty database."""
        result = items_service.list_items()
        
        assert result["total"] == 0
        assert len(result["items"]) == 0
        assert result["page"] == 1
        assert result["per_page"] == 20
        assert result["total_pages"] == 0
