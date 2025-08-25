"""Tests for stats API endpoints."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, UTC, timedelta

from app.models.database import Item, Attempt


class TestStatsAPI:
    """Test cases for stats API endpoints."""

    def test_get_summary_stats_success(self, test_client, db_manager):
        """Test successful summary statistics retrieval."""
        # Create items and attempts
        with db_manager.get_session() as session:
            item1 = Item(
                locale="fi",
                text="Item 1",
                tts_status="ready"
            )
            item2 = Item(
                locale="fi",
                text="Item 2",
                tts_status="ready"
            )
            session.add_all([item1, item2])
            session.commit()
            session.refresh(item1)
            session.refresh(item2)
            
            # Create attempts
            for i in range(3):
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
                text="Single attempt",
                percentage=75,
                wer=0.25,
                words_ref=4,
                words_correct=3
            )
            session.add(attempt)
            session.commit()
        
        # Get summary stats
        response = test_client.get("/v1/stats/summary")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["attempts"] == 4
        assert data["audios_practiced"] == 2
        assert data["avg_percentage"] > 0
        assert data["avg_wer"] > 0

    def test_get_summary_stats_with_time_window(self, test_client, db_manager):
        """Test summary statistics with time window."""
        # Create items and attempts
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
            
            # Old attempt (outside window)
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
            
            # Recent attempt (within window)
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
        
        # Get stats for last 5 days
        since = (now - timedelta(days=5)).isoformat()
        response = test_client.get(f"/v1/stats/summary?since={since}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["attempts"] == 1  # Only recent attempt
        assert data["audios_practiced"] == 1

    def test_get_summary_stats_invalid_time_window(self, test_client):
        """Test summary statistics with invalid time window."""
        # since > until should return 400
        now = datetime.now(UTC)
        since = now.isoformat()
        until = (now - timedelta(days=1)).isoformat()
        
        response = test_client.get(f"/v1/stats/summary?since={since}&until={until}")
        
        assert response.status_code == 400
        data = response.json()
        assert "'since' must be before 'until'" in data["detail"]

    def test_get_summary_stats_empty_database(self, test_client):
        """Test summary statistics from empty database."""
        response = test_client.get("/v1/stats/summary")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["attempts"] == 0
        assert data["audios_practiced"] == 0
        assert data["avg_percentage"] == 0.0
        assert data["avg_wer"] == 0.0

    def test_get_practice_log_success(self, test_client, db_manager):
        """Test successful practice log retrieval."""
        # Create items and attempts
        with db_manager.get_session() as session:
            item1 = Item(
                locale="fi",
                text="Item 1",
                tts_status="ready"
            )
            item2 = Item(
                locale="fi",
                text="Item 2",
                tts_status="ready"
            )
            session.add_all([item1, item2])
            session.commit()
            session.refresh(item1)
            session.refresh(item2)
            
            # Create multiple attempts for item1
            for i in range(3):
                attempt = Attempt(
                    item_id=item1.id,
                    text=f"Attempt {i}",
                    percentage=80 + i * 5,
                    wer=0.2 - i * 0.05,
                    words_ref=5,
                    words_correct=4 + i
                )
                session.add(attempt)
            
            # Create single attempt for item2
            attempt = Attempt(
                item_id=item2.id,
                text="Single attempt",
                percentage=75,
                wer=0.25,
                words_ref=4,
                words_correct=3
            )
            session.add(attempt)
            session.commit()
        
        # Get practice log
        response = test_client.get("/v1/stats/practice-log")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 2
        assert len(data["practice_log"]) == 2
        assert data["page"] == 1
        assert data["per_page"] == 20
        
        # Check item1 stats
        item1_log = next(log for log in data["practice_log"] if log["item_id"] == item1.id)
        assert item1_log["attempts_count"] == 3
        assert item1_log["avg_percentage"] > 80
        assert item1_log["best_percentage"] == 90

    def test_get_practice_log_with_pagination(self, test_client, db_manager):
        """Test practice log with pagination."""
        # Create many items with attempts
        with db_manager.get_session() as session:
            for i in range(25):
                item = Item(
                    locale="fi",
                    text=f"Item {i}",
                    tts_status="ready"
                )
                session.add(item)
                session.commit()
                session.refresh(item)
                
                # Create attempt for each item
                attempt = Attempt(
                    item_id=item.id,
                    text=f"Attempt for item {i}",
                    percentage=70 + i,
                    wer=0.3,
                    words_ref=5,
                    words_correct=4
                )
                session.add(attempt)
                session.commit()
        
        # Get practice log with pagination
        response = test_client.get("/v1/stats/practice-log?page=2&per_page=10")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 25
        assert data["page"] == 2
        assert data["per_page"] == 10
        assert data["total_pages"] == 3
        assert len(data["practice_log"]) == 10

    def test_get_practice_log_with_time_window(self, test_client, db_manager):
        """Test practice log with time window."""
        # Create items and attempts
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
        
        # Get practice log for last 5 days
        since = (now - timedelta(days=5)).isoformat()
        response = test_client.get(f"/v1/stats/practice-log?since={since}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1  # Only recent attempt
        assert len(data["practice_log"]) == 1

    def test_get_practice_log_invalid_time_window(self, test_client):
        """Test practice log with invalid time window."""
        # since > until should return 400
        now = datetime.now(UTC)
        since = now.isoformat()
        until = (now - timedelta(days=1)).isoformat()
        
        response = test_client.get(f"/v1/stats/practice-log?since={since}&until={until}")
        
        assert response.status_code == 400
        data = response.json()
        assert "'since' must be before 'until'" in data["detail"]

    def test_get_practice_log_invalid_pagination(self, test_client):
        """Test practice log with invalid pagination parameters."""
        # Invalid page number
        response = test_client.get("/v1/stats/practice-log?page=0")
        assert response.status_code == 422
        
        # Invalid per_page
        response = test_client.get("/v1/stats/practice-log?per_page=0")
        assert response.status_code == 422
        
        response = test_client.get("/v1/stats/practice-log?per_page=101")
        assert response.status_code == 422

    def test_get_item_stats_success(self, test_client, db_manager):
        """Test successful item statistics retrieval."""
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
            
            # Create multiple attempts
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
        
        # Get item stats
        response = test_client.get(f"/v1/stats/items/{item.id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["item_id"] == item.id
        assert data["attempts_count"] == 3
        assert data["avg_percentage"] > 80
        assert data["best_percentage"] == 90
        assert data["worst_percentage"] == 80
        assert data["avg_wer"] > 0
        assert data["best_wer"] < data["worst_wer"]

    def test_get_item_stats_not_found(self, test_client):
        """Test getting stats for non-existent item."""
        response = test_client.get("/v1/stats/items/999")
        
        assert response.status_code == 404
        data = response.json()
        assert "Item not found" in data["detail"]

    def test_get_item_stats_no_attempts(self, test_client, db_manager):
        """Test getting stats for item with no attempts."""
        # Create item without attempts
        with db_manager.get_session() as session:
            item = Item(
                locale="fi",
                text="Item without attempts",
                tts_status="ready"
            )
            session.add(item)
            session.commit()
            session.refresh(item)
        
        # Get item stats
        response = test_client.get(f"/v1/stats/items/{item.id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["attempts_count"] == 0
        assert data["avg_percentage"] == 0.0
        assert data["best_percentage"] == 0
        assert data["worst_percentage"] == 0

    def test_get_progress_over_time_success(self, test_client, db_manager):
        """Test successful progress over time retrieval."""
        # Create item and attempts over time
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
            
            # Create attempts on different days
            for i in range(5):
                attempt = Attempt(
                    item_id=item.id,
                    text=f"Attempt {i}",
                    percentage=70 + i * 5,
                    wer=0.3 - i * 0.05,
                    words_ref=5,
                    words_correct=4 + i
                )
                attempt.created_at = now - timedelta(days=i)
                session.add(attempt)
            session.commit()
        
        # Get progress over last 10 days
        response = test_client.get(f"/v1/stats/progress?item_id={item.id}&days=10")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "progress" in data
        assert len(data["progress"]) > 0
        
        for entry in data["progress"]:
            assert "date" in entry
            assert "attempts" in entry
            assert "avg_percentage" in entry
            assert "avg_wer" in entry

    def test_get_progress_over_time_all_items(self, test_client, db_manager):
        """Test progress over time for all items."""
        # Create multiple items with attempts
        with db_manager.get_session() as session:
            for i in range(3):
                item = Item(
                    locale="fi",
                    text=f"Item {i}",
                    tts_status="ready"
                )
                session.add(item)
                session.commit()
                session.refresh(item)
                
                # Create attempt for each item
                attempt = Attempt(
                    item_id=item.id,
                    text=f"Attempt for item {i}",
                    percentage=80 + i * 5,
                    wer=0.2 - i * 0.05,
                    words_ref=5,
                    words_correct=4 + i
                )
                session.add(attempt)
            session.commit()
        
        # Get progress for all items
        response = test_client.get("/v1/stats/progress?days=30")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "progress" in data
        assert len(data["progress"]) > 0
        
        for entry in data["progress"]:
            assert "date" in entry
            assert "attempts" in entry

    def test_get_progress_over_time_custom_days(self, test_client, db_manager):
        """Test progress over time with custom day range."""
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
            
            # Create attempts on different days
            for i in range(10):
                attempt = Attempt(
                    item_id=item.id,
                    text=f"Attempt {i}",
                    percentage=80,
                    wer=0.2,
                    words_ref=5,
                    words_correct=4
                )
                attempt.created_at = now - timedelta(days=i)
                session.add(attempt)
            session.commit()
        
        # Get progress for last 5 days
        response = test_client.get(f"/v1/stats/progress?item_id={item.id}&days=5")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["progress"]) <= 5  # Should not exceed requested days

    def test_get_progress_over_time_invalid_days(self, test_client):
        """Test progress over time with invalid days parameter."""
        # Days out of range
        response = test_client.get("/v1/stats/progress?days=0")
        assert response.status_code == 422
        
        response = test_client.get("/v1/stats/progress?days=366")
        assert response.status_code == 422

    def test_get_progress_over_time_empty_database(self, test_client):
        """Test progress over time from empty database."""
        response = test_client.get("/v1/stats/progress?days=30")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "progress" in data
        assert len(data["progress"]) == 0

    def test_stats_response_structure(self, test_client, db_manager):
        """Test that all stats endpoints return correct response structure."""
        # Create a test item and attempt
        with db_manager.get_session() as session:
            item = Item(
                locale="fi",
                text="Test item",
                tts_status="ready"
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            
            attempt = Attempt(
                item_id=item.id,
                text="Test attempt",
                percentage=80,
                wer=0.2,
                words_ref=5,
                words_correct=4
            )
            session.add(attempt)
            session.commit()
        
        # Test summary stats structure
        response = test_client.get("/v1/stats/summary")
        assert response.status_code == 200
        data = response.json()
        
        required_fields = ["attempts", "audios_practiced", "avg_percentage", "avg_wer"]
        for field in required_fields:
            assert field in data
        
        # Test practice log structure
        response = test_client.get("/v1/stats/practice-log")
        assert response.status_code == 200
        data = response.json()
        
        required_fields = ["practice_log", "total", "page", "per_page", "total_pages"]
        for field in required_fields:
            assert field in data
        
        if data["practice_log"]:
            entry = data["practice_log"][0]
            required_entry_fields = [
                "item_id", "text", "audio_url", "attempts_count", "first_attempt_at",
                "last_attempt_at", "avg_percentage", "best_percentage", "avg_wer"
            ]
            for field in required_entry_fields:
                assert field in entry
        
        # Test item stats structure
        response = test_client.get(f"/v1/stats/items/{item.id}")
        assert response.status_code == 200
        data = response.json()
        
        required_fields = [
            "item_id", "text", "audio_url", "attempts_count", "first_attempt_at",
            "last_attempt_at", "avg_percentage", "best_percentage", "worst_percentage",
            "avg_wer", "best_wer", "worst_wer"
        ]
        for field in required_fields:
            assert field in data
        
        # Test progress structure
        response = test_client.get(f"/v1/stats/progress?item_id={item.id}&days=30")
        assert response.status_code == 200
        data = response.json()
        
        assert "progress" in data
        if data["progress"]:
            entry = data["progress"][0]
            required_entry_fields = ["date", "attempts", "avg_percentage", "avg_wer"]
            for field in required_entry_fields:
                assert field in entry

    def test_stats_calculation_accuracy(self, test_client, db_manager):
        """Test accuracy of statistical calculations."""
        # Create item with known attempt values
        with db_manager.get_session() as session:
            item = Item(
                locale="fi",
                text="Test item",
                tts_status="ready"
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            
            # Create attempts with known values
            attempts_data = [
                {"percentage": 80, "wer": 0.2},
                {"percentage": 90, "wer": 0.1},
                {"percentage": 70, "wer": 0.3},
            ]
            
            for i, data in enumerate(attempts_data):
                attempt = Attempt(
                    item_id=item.id,
                    text=f"Attempt {i}",
                    percentage=data["percentage"],
                    wer=data["wer"],
                    words_ref=5,
                    words_correct=4
                )
                session.add(attempt)
            session.commit()
        
        # Get item stats
        response = test_client.get(f"/v1/stats/items/{item.id}")
        assert response.status_code == 200
        data = response.json()
        
        # Verify calculations
        assert data["attempts_count"] == 3
        assert data["avg_percentage"] == 80.0  # (80 + 90 + 70) / 3
        assert data["best_percentage"] == 90
        assert data["worst_percentage"] == 70
        assert abs(data["avg_wer"] - 0.2) < 0.001  # (0.2 + 0.1 + 0.3) / 3
        assert data["best_wer"] == 0.1
        assert data["worst_wer"] == 0.3

    def test_stats_edge_cases(self, test_client, db_manager):
        """Test edge cases and boundary conditions."""
        # Test with very large numbers
        with db_manager.get_session() as session:
            item = Item(
                locale="fi",
                text="Edge case item",
                tts_status="ready"
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            
            # Create attempt with edge case values
            attempt = Attempt(
                item_id=item.id,
                text="Edge case attempt",
                percentage=100,  # Perfect score
                wer=0.0,  # Perfect WER
                words_ref=1,  # Single word
                words_correct=1
            )
            session.add(attempt)
            session.commit()
        
        # Get stats
        response = test_client.get(f"/v1/stats/items/{item.id}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["avg_percentage"] == 100.0
        assert data["avg_wer"] == 0.0
        assert data["best_percentage"] == 100
        assert data["worst_percentage"] == 100

    def test_stats_time_window_edge_cases(self, test_client):
        """Test time window edge cases."""
        # Test with same start and end time
        now = datetime.now(UTC)
        since = now.isoformat()
        until = now.isoformat()
        
        response = test_client.get(f"/v1/stats/summary?since={since}&until={until}")
        assert response.status_code == 200
        
        # Test with None time values (should work)
        response = test_client.get("/v1/stats/summary")
        assert response.status_code == 200
        
        # Test with future dates (should work but return empty results)
        future = (now + timedelta(days=1)).isoformat()
        response = test_client.get(f"/v1/stats/summary?since={future}")
        assert response.status_code == 200

    def test_stats_pagination_edge_cases(self, test_client):
        """Test pagination edge cases."""
        # Test with page 1 (should work)
        response = test_client.get("/v1/stats/practice-log?page=1")
        assert response.status_code == 200
        
        # Test with per_page at boundaries
        response = test_client.get("/v1/stats/practice-log?per_page=1")
        assert response.status_code == 200
        
        response = test_client.get("/v1/stats/practice-log?per_page=100")
        assert response.status_code == 200

    def test_stats_filtering_combinations(self, test_client, db_manager):
        """Test combinations of different filters."""
        # Create test data
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
            
            # Create attempts at different times
            for i in range(5):
                attempt = Attempt(
                    item_id=item.id,
                    text=f"Attempt {i}",
                    percentage=80 + i,
                    wer=0.2,
                    words_ref=5,
                    words_correct=4
                )
                attempt.created_at = now - timedelta(days=i)
                session.add(attempt)
            session.commit()
        
        # Test combination of time window and pagination
        since = (now - timedelta(days=3)).isoformat()
        response = test_client.get(f"/v1/stats/practice-log?since={since}&page=1&per_page=2")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have attempts from last 3 days
        assert data["total"] <= 3
        assert len(data["practice_log"]) <= 2

    def test_stats_error_handling(self, test_client):
        """Test error handling in stats endpoints."""
        # Test with invalid item ID
        response = test_client.get("/v1/stats/items/invalid")
        assert response.status_code == 422
        
        # Test with non-existent item ID
        response = test_client.get("/v1/stats/items/999")
        assert response.status_code == 404
        
        # Test with invalid time parameters
        response = test_client.get("/v1/stats/summary?since=invalid_date")
        assert response.status_code == 422
        
        # Test with invalid pagination
        response = test_client.get("/v1/stats/practice-log?page=-1")
        assert response.status_code == 422
