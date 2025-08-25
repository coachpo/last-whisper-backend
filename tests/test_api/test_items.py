"""Tests for items API endpoints."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, UTC

from app.models.database import Item, Attempt


class TestItemsAPI:
    """Test cases for items API endpoints."""

    def test_create_item_success(self, test_client, sample_item_data):
        """Test successful item creation."""
        response = test_client.post("/v1/items", json=sample_item_data)
        
        assert response.status_code == 202
        data = response.json()
        
        assert data["locale"] == "fi"
        assert data["text"] == "Hei, tämä on testi!"
        assert data["difficulty"] == 3
        assert data["tags"] == ["test", "basic"]
        assert data["tts_status"] == "pending"
        assert data["audio_url"] is None
        assert "created_at" in data
        assert "updated_at" in data
        assert data["practiced"] is False

    def test_create_item_without_optional_fields(self, test_client):
        """Test item creation without optional fields."""
        item_data = {
            "locale": "en",
            "text": "Simple English text"
        }
        
        response = test_client.post("/v1/items", json=item_data)
        
        assert response.status_code == 202
        data = response.json()
        
        assert data["locale"] == "en"
        assert data["text"] == "Simple English text"
        assert data["difficulty"] is None
        assert data["tags"] == []
        assert data["tts_status"] == "pending"

    def test_create_item_invalid_data(self, test_client):
        """Test item creation with invalid data."""
        # Missing required fields
        response = test_client.post("/v1/items", json={})
        assert response.status_code == 422
        
        # Invalid locale
        response = test_client.post("/v1/items", json={
            "locale": "invalid_locale",
            "text": "Test text"
        })
        assert response.status_code == 422
        
        # Empty text
        response = test_client.post("/v1/items", json={
            "locale": "fi",
            "text": ""
        })
        assert response.status_code == 422
        
        # Invalid difficulty
        response = test_client.post("/v1/items", json={
            "locale": "fi",
            "text": "Test text",
            "difficulty": 11  # Out of range
        })
        assert response.status_code == 422

    def test_create_item_invalid_tags(self, test_client):
        """Test item creation with invalid tags."""
        # Too many tags
        too_many_tags = [f"tag{i}" for i in range(21)]
        response = test_client.post("/v1/items", json={
            "locale": "fi",
            "text": "Test text",
            "tags": too_many_tags
        })
        assert response.status_code == 422
        
        # Empty tag
        response = test_client.post("/v1/items", json={
            "locale": "fi",
            "text": "Test text",
            "tags": ["valid_tag", ""]
        })
        assert response.status_code == 422
        
        # Tag too long
        long_tag = "a" * 51
        response = test_client.post("/v1/items", json={
            "locale": "fi",
            "text": "Test text",
            "tags": [long_tag]
        })
        assert response.status_code == 422

    def test_list_items_basic(self, test_client, db_manager):
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
        
        response = test_client.get("/v1/items")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 3
        assert len(data["items"]) == 3
        assert data["page"] == 1
        assert data["per_page"] == 20
        assert data["total_pages"] == 1

    def test_list_items_with_locale_filter(self, test_client, db_manager):
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
        response = test_client.get("/v1/items?locale=fi")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all(item["locale"] == "fi" for item in data["items"])

    def test_list_items_with_tags_filter(self, test_client, db_manager):
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
        response = test_client.get("/v1/items?tag=test")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert "test" in data["items"][0]["tags"]

    def test_list_items_with_multiple_tags_filter(self, test_client, db_manager):
        """Test item listing with multiple tags filter."""
        # Create items with different tags
        with db_manager.get_session() as session:
            item1 = Item(
                locale="fi",
                text="Item with test and basic tags",
                tts_status="ready"
            )
            item1.tags = ["test", "basic"]
            session.add(item1)
            
            item2 = Item(
                locale="fi",
                text="Item with only test tag",
                tts_status="ready"
            )
            item2.tags = ["test"]
            session.add(item2)
            
            session.commit()
        
        # Filter by multiple tags (should find items with ALL tags)
        response = test_client.get("/v1/items?tag=test&tag=basic")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1  # Only item1 has both tags
        assert "test" in data["items"][0]["tags"]
        assert "basic" in data["items"][0]["tags"]

    def test_list_items_with_difficulty_filter_single(self, test_client, db_manager):
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
        response = test_client.get("/v1/items?difficulty=2")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["difficulty"] == 2

    def test_list_items_with_difficulty_filter_range(self, test_client, db_manager):
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
        response = test_client.get("/v1/items?difficulty=2..4")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert all(2 <= item["difficulty"] <= 4 for item in data["items"])

    def test_list_items_with_text_search(self, test_client, db_manager):
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
        response = test_client.get("/v1/items?q=testi")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert "testi" in data["items"][0]["text"]

    def test_list_items_with_practiced_filter(self, test_client, db_manager):
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
        response = test_client.get("/v1/items?practiced=true")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["text"] == "Practiced item"
        
        # Filter by unpracticed items
        response = test_client.get("/v1/items?practiced=false")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["text"] == "Unpracticed item"

    def test_list_items_with_sorting(self, test_client, db_manager):
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
            response = test_client.get(f"/v1/items?sort={sort}")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 3
            assert len(data["items"]) == 3

    def test_list_items_with_invalid_sort(self, test_client):
        """Test item listing with invalid sort parameter."""
        response = test_client.get("/v1/items?sort=invalid_sort")
        
        assert response.status_code == 400
        data = response.json()
        assert "Invalid sort parameter" in data["detail"]

    def test_list_items_with_pagination(self, test_client, db_manager):
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
        response = test_client.get("/v1/items?page=2&per_page=10")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 25
        assert data["page"] == 2
        assert data["per_page"] == 10
        assert data["total_pages"] == 3
        assert len(data["items"]) == 10

    def test_list_items_invalid_pagination(self, test_client):
        """Test item listing with invalid pagination parameters."""
        # Invalid page number
        response = test_client.get("/v1/items?page=0")
        assert response.status_code == 422
        
        # Invalid per_page
        response = test_client.get("/v1/items?per_page=0")
        assert response.status_code == 422
        
        response = test_client.get("/v1/items?per_page=101")
        assert response.status_code == 422

    def test_get_item_success(self, test_client, db_manager):
        """Test successful item retrieval."""
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
            
            item_id = item.id
        
        # Get item
        response = test_client.get(f"/v1/items/{item_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == item_id
        assert data["locale"] == "fi"
        assert data["text"] == "Test item"
        assert data["difficulty"] == 3
        assert data["tags"] == ["test", "basic"]
        assert data["tts_status"] == "ready"
        assert data["audio_url"] == "/audio/test.wav"

    def test_get_item_not_found(self, test_client):
        """Test getting non-existent item."""
        response = test_client.get("/v1/items/999")
        
        assert response.status_code == 404
        data = response.json()
        assert "Item not found" in data["detail"]

    def test_get_item_invalid_id(self, test_client):
        """Test getting item with invalid ID."""
        response = test_client.get("/v1/items/invalid")
        
        assert response.status_code == 422

    def test_delete_item_success(self, test_client, db_manager):
        """Test successful item deletion."""
        # Create an item
        with db_manager.get_session() as session:
            item = Item(
                locale="fi",
                text="Item to delete",
                tts_status="ready"
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            
            item_id = item.id
        
        # Delete item
        response = test_client.delete(f"/v1/items/{item_id}")
        
        assert response.status_code == 204
        
        # Verify item was deleted
        with db_manager.get_session() as session:
            deleted_item = session.query(Item).filter(Item.id == item_id).first()
            assert deleted_item is None

    def test_delete_item_not_found(self, test_client):
        """Test deleting non-existent item."""
        response = test_client.delete("/v1/items/999")
        
        assert response.status_code == 404
        data = response.json()
        assert "Item not found" in data["detail"]

    def test_delete_item_invalid_id(self, test_client):
        """Test deleting item with invalid ID."""
        response = test_client.delete("/v1/items/invalid")
        
        assert response.status_code == 422

    def test_get_item_audio_success(self, test_client, db_manager):
        """Test successful audio file retrieval."""
        # Create an item with ready TTS status
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
        
        # Mock file existence
        with patch('os.path.exists', return_value=True):
            response = test_client.get(f"/v1/items/{item_id}/audio")
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "audio/wav"

    def test_get_item_audio_not_found(self, test_client):
        """Test getting audio for non-existent item."""
        response = test_client.get("/v1/items/999/audio")
        
        assert response.status_code == 404
        data = response.json()
        assert "Item not found" in data["detail"]

    def test_get_item_audio_not_ready(self, test_client, db_manager):
        """Test getting audio for item with TTS not ready."""
        # Create an item with pending TTS status
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
        
        response = test_client.get(f"/v1/items/{item_id}/audio")
        
        assert response.status_code == 400
        data = response.json()
        assert "Audio not ready" in data["detail"]

    def test_get_item_audio_file_not_found(self, test_client, db_manager):
        """Test getting audio when file doesn't exist."""
        # Create an item with ready TTS status
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
        
        # Mock file not existing
        with patch('os.path.exists', return_value=False):
            response = test_client.get(f"/v1/items/{item_id}/audio")
            
            assert response.status_code == 404
            data = response.json()
            assert "Audio file not found" in data["detail"]

    def test_list_items_empty_database(self, test_client):
        """Test item listing from empty database."""
        response = test_client.get("/v1/items")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 0
        assert len(data["items"]) == 0
        assert data["page"] == 1
        assert data["per_page"] == 20
        assert data["total_pages"] == 0

    def test_create_item_enqueues_tts_job(self, test_client, sample_item_data, mock_task_manager):
        """Test that TTS job is enqueued when creating item."""
        response = test_client.post("/v1/items", json=sample_item_data)
        
        assert response.status_code == 202
        
        # Verify TTS job was submitted
        mock_task_manager.submit_task_for_item.assert_called_once()

    def test_create_item_tts_job_failure(self, test_client, sample_item_data, mock_task_manager):
        """Test item creation when TTS job fails."""
        mock_task_manager.submit_task_for_item.side_effect = Exception("TTS service error")
        
        response = test_client.post("/v1/items", json=sample_item_data)
        
        # Item should still be created
        assert response.status_code == 202
        data = response.json()
        assert data["tts_status"] == "failed"

    def test_item_practiced_status(self, test_client, db_manager):
        """Test that practiced status is correctly calculated."""
        # Create an item
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
        
        # Initially should not be practiced
        response = test_client.get(f"/v1/items/{item_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["practiced"] is False
        
        # Create an attempt
        attempt_data = {
            "item_id": item_id,
            "text": "User attempt"
        }
        response = test_client.post("/v1/attempts", json=attempt_data)
        assert response.status_code == 201
        
        # Now should be practiced
        response = test_client.get(f"/v1/items/{item_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["practiced"] is True

    def test_item_timestamps(self, test_client, sample_item_data):
        """Test that item timestamps are properly set."""
        response = test_client.post("/v1/items", json=sample_item_data)
        
        assert response.status_code == 202
        data = response.json()
        
        # Should have created_at and updated_at timestamps
        assert "created_at" in data
        assert "updated_at" in data
        assert data["created_at"] is not None
        assert data["updated_at"] is not None
        
        # Timestamps should be recent
        created_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
        updated_at = datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))
        now = datetime.now(UTC)
        
        time_diff_created = abs((now - created_at).total_seconds())
        time_diff_updated = abs((now - updated_at).total_seconds())
        
        # Should be within last minute
        assert time_diff_created < 60
        assert time_diff_updated < 60
