"""Tests for attempts API endpoints."""

import pytest
from datetime import datetime, UTC, timedelta

from app.models.database import Item, Attempt


class TestAttemptsAPI:
    """Test cases for attempts API endpoints."""

    def test_create_attempt_success(self, test_client, db_manager):
        """Test successful attempt creation."""
        # Create an item first
        with db_manager.get_session() as session:
            item = Item(
                locale="fi",
                text="Hei, tämä on testi!",
                tts_status="ready"
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            
            item_id = item.id
        
        # Create attempt
        attempt_data = {
            "item_id": item_id,
            "text": "Hei, tämä on testi!"
        }
        
        response = test_client.post("/v1/attempts", json=attempt_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["item_id"] == item_id
        assert data["text"] == "Hei, tämä on testi!"
        assert "percentage" in data
        assert "wer" in data
        assert "words_ref" in data
        assert "words_correct" in data
        assert "created_at" in data

    def test_create_attempt_item_not_found(self, test_client):
        """Test attempt creation with non-existent item."""
        attempt_data = {
            "item_id": 999,
            "text": "Test text"
        }
        
        response = test_client.post("/v1/attempts", json=attempt_data)
        
        assert response.status_code == 404
        data = response.json()
        assert "Item not found" in data["detail"]

    def test_create_attempt_invalid_data(self, test_client):
        """Test attempt creation with invalid data."""
        # Missing required fields
        response = test_client.post("/v1/attempts", json={})
        
        assert response.status_code == 422
        
        # Invalid item_id type
        response = test_client.post("/v1/attempts", json={
            "item_id": "invalid",
            "text": "Test text"
        })
        
        assert response.status_code == 422

    def test_create_attempt_empty_text(self, test_client, db_manager):
        """Test attempt creation with empty text."""
        # Create an item first
        with db_manager.get_session() as session:
            item = Item(
                locale="fi",
                text="Reference text",
                tts_status="ready"
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            
            item_id = item.id
        
        # Create attempt with empty text
        attempt_data = {
            "item_id": item_id,
            "text": ""
        }
        
        response = test_client.post("/v1/attempts", json=attempt_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["percentage"] == 0  # Should score 0 for empty text

    def test_list_attempts_basic(self, test_client, db_manager):
        """Test basic attempt listing."""
        # Create items and attempts
        with db_manager.get_session() as session:
            item = Item(
                locale="fi",
                text="Reference text",
                tts_status="ready"
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            
            for i in range(3):
                attempt = Attempt(
                    item_id=item.id,
                    text=f"Attempt {i}",
                    percentage=80 + i * 5,
                    wer=0.2 - i * 0.05,
                    words_ref=5,
                    words_correct=4 + i
                )
                session.add(attempt)
            session.commit()
        
        # List attempts
        response = test_client.get("/v1/attempts")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 3
        assert len(data["attempts"]) == 3
        assert data["page"] == 1
        assert data["per_page"] == 20
        assert data["total_pages"] == 1

    def test_list_attempts_with_filters(self, test_client, db_manager):
        """Test attempt listing with filters."""
        # Create items and attempts
        with db_manager.get_session() as session:
            item1 = Item(
                locale="fi",
                text="Item 1",
                tts_status="ready"
            )
            item2 = Item(
                locale="en",
                text="Item 2",
                tts_status="ready"
            )
            session.add_all([item1, item2])
            session.commit()
            session.refresh(item1)
            session.refresh(item2)
            
            # Create attempts for item1
            for i in range(2):
                attempt = Attempt(
                    item_id=item1.id,
                    text=f"Attempt {i}",
                    percentage=80 + i * 5,
                    wer=0.2 - i * 0.05,
                    words_ref=5,
                    words_correct=4 + i
                )
                session.add(attempt)
            
            # Create attempt for item2
            attempt = Attempt(
                item_id=item2.id,
                text="English attempt",
                percentage=75,
                wer=0.25,
                words_ref=4,
                words_correct=3
            )
            session.add(attempt)
            session.commit()
        
        # Filter by item_id
        response = test_client.get(f"/v1/attempts?item_id={item1.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all(attempt["item_id"] == item1.id for attempt in data["attempts"])

    def test_list_attempts_with_time_filters(self, test_client, db_manager):
        """Test attempt listing with time filters."""
        # Create item and attempts
        with db_manager.get_session() as session:
            item = Item(
                locale="fi",
                text="Test item",
                tts_status="ready"
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            
            now = datetime.now(UTC)
            
            # Old attempt
            old_attempt = Attempt(
                item_id=item.id,
                text="Old attempt",
                percentage=70,
                wer=0.3,
                words_ref=5,
                words_correct=4
            )
            old_attempt.created_at = now - timedelta(days=10)
            session.add(old_attempt)
            
            # Recent attempt
            recent_attempt = Attempt(
                item_id=item.id,
                text="Recent attempt",
                percentage=85,
                wer=0.15,
                words_ref=5,
                words_correct=4
            )
            recent_attempt.created_at = now - timedelta(days=2)
            session.add(recent_attempt)
            
            session.commit()
        
        # Filter by time window
        since = (now - timedelta(days=5)).isoformat()
        response = test_client.get(f"/v1/attempts?since={since}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1  # Only recent attempt

    def test_list_attempts_with_pagination(self, test_client, db_manager):
        """Test attempt listing with pagination."""
        # Create many attempts
        with db_manager.get_session() as session:
            item = Item(
                locale="fi",
                text="Reference text",
                tts_status="ready"
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            
            for i in range(25):
                attempt = Attempt(
                    item_id=item.id,
                    text=f"Attempt {i}",
                    percentage=70 + i,
                    wer=0.3,
                    words_ref=5,
                    words_correct=4
                )
                session.add(attempt)
            session.commit()
        
        # Test pagination
        response = test_client.get("/v1/attempts?page=2&per_page=10")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 25
        assert data["page"] == 2
        assert data["per_page"] == 10
        assert data["total_pages"] == 3
        assert len(data["attempts"]) == 10

    def test_list_attempts_invalid_pagination(self, test_client):
        """Test attempt listing with invalid pagination parameters."""
        # Invalid page number
        response = test_client.get("/v1/attempts?page=0")
        assert response.status_code == 422
        
        # Invalid per_page
        response = test_client.get("/v1/attempts?per_page=0")
        assert response.status_code == 422
        
        response = test_client.get("/v1/attempts?per_page=101")
        assert response.status_code == 422

    def test_get_attempt_success(self, test_client, db_manager):
        """Test successful attempt retrieval."""
        # Create item and attempt
        with db_manager.get_session() as session:
            item = Item(
                locale="fi",
                text="Reference text",
                tts_status="ready"
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            
            attempt = Attempt(
                item_id=item.id,
                text="User attempt",
                percentage=80,
                wer=0.2,
                words_ref=5,
                words_correct=4
            )
            session.add(attempt)
            session.commit()
            session.refresh(attempt)
            
            attempt_id = attempt.id
        
        # Get attempt
        response = test_client.get(f"/v1/attempts/{attempt_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == attempt_id
        assert data["item_id"] == item.id
        assert data["text"] == "User attempt"
        assert data["percentage"] == 80
        assert data["wer"] == 0.2

    def test_get_attempt_not_found(self, test_client):
        """Test getting non-existent attempt."""
        response = test_client.get("/v1/attempts/999")
        
        assert response.status_code == 404
        data = response.json()
        assert "Attempt not found" in data["detail"]

    def test_get_attempt_invalid_id(self, test_client):
        """Test getting attempt with invalid ID."""
        response = test_client.get("/v1/attempts/invalid")
        
        assert response.status_code == 422

    def test_list_attempts_empty_database(self, test_client):
        """Test attempt listing from empty database."""
        response = test_client.get("/v1/attempts")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 0
        assert len(data["attempts"]) == 0
        assert data["page"] == 1
        assert data["per_page"] == 20
        assert data["total_pages"] == 0

    def test_create_attempt_percentage_calculation(self, test_client, db_manager):
        """Test that attempt percentage is calculated correctly."""
        # Create an item
        with db_manager.get_session() as session:
            item = Item(
                locale="fi",
                text="Hei, tämä on testi!",
                tts_status="ready"
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            
            item_id = item.id
        
        # Create attempt with perfect match
        attempt_data = {
            "item_id": item_id,
            "text": "Hei, tämä on testi!"
        }
        
        response = test_client.post("/v1/attempts", json=attempt_data)
        
        assert response.status_code == 201
        data = response.json()
        
        # Should have high percentage for perfect match
        assert data["percentage"] >= 90
        
        # Create attempt with partial match
        attempt_data["text"] = "Hei, tämä testi!"
        
        response = test_client.post("/v1/attempts", json=attempt_data)
        
        assert response.status_code == 201
        data = response.json()
        
        # Should have lower percentage for partial match
        assert data["percentage"] < 100
        assert data["percentage"] > 0

    def test_create_attempt_wer_calculation(self, test_client, db_manager):
        """Test that Word Error Rate is calculated correctly."""
        # Create an item
        with db_manager.get_session() as session:
            item = Item(
                locale="fi",
                text="Hei, tämä on testi!",
                tts_status="ready"
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            
            item_id = item.id
        
        # Create attempt
        attempt_data = {
            "item_id": item_id,
            "text": "Hei, tämä on testi!"
        }
        
        response = test_client.post("/v1/attempts", json=attempt_data)
        
        assert response.status_code == 201
        data = response.json()
        
        # WER should be between 0 and 1
        assert data["wer"] >= 0.0
        assert data["wer"] <= 1.0
        
        # Perfect match should have WER close to 0
        if data["percentage"] >= 95:
            assert data["wer"] < 0.1

    def test_create_attempt_words_counting(self, test_client, db_manager):
        """Test that word counts are calculated correctly."""
        # Create an item with known word count
        with db_manager.get_session() as session:
            item = Item(
                locale="fi",
                text="Hei, tämä on testi!",
                tts_status="ready"
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            
            item_id = item.id
        
        # Create attempt
        attempt_data = {
            "item_id": item_id,
            "text": "Hei, tämä on testi!"
        }
        
        response = test_client.post("/v1/attempts", json=attempt_data)
        
        assert response.status_code == 201
        data = response.json()
        
        # Should have correct word counts
        assert data["words_ref"] > 0
        assert data["words_correct"] >= 0
        assert data["words_correct"] <= data["words_ref"]
        
        # For perfect match, words_correct should equal words_ref
        if data["percentage"] == 100:
            assert data["words_correct"] == data["words_ref"]

    def test_create_attempt_timestamps(self, test_client, db_manager):
        """Test that timestamps are properly set."""
        # Create an item
        with db_manager.get_session() as session:
            item = Item(
                locale="fi",
                text="Test text",
                tts_status="ready"
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            
            item_id = item.id
        
        # Create attempt
        attempt_data = {
            "item_id": item_id,
            "text": "Test text"
        }
        
        response = test_client.post("/v1/attempts", json=attempt_data)
        
        assert response.status_code == 201
        data = response.json()
        
        # Should have created_at timestamp
        assert "created_at" in data
        assert data["created_at"] is not None
        
        # Timestamp should be recent
        created_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
        now = datetime.now(UTC)
        time_diff = abs((now - created_at).total_seconds())
        
        # Should be within last minute
        assert time_diff < 60
