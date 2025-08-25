"""Tests for StatsService."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, UTC, timedelta

from app.services.stats_service import StatsService
from app.models.database import Attempt, Item


class TestStatsService:
    """Test cases for StatsService."""

    @pytest.fixture
    def stats_service(self, db_manager):
        """Create a stats service instance for testing."""
        return StatsService(db_manager)

    def test_init(self, db_manager):
        """Test service initialization."""
        service = StatsService(db_manager)
        assert service.db_manager == db_manager

    def test_get_summary_stats_basic(self, stats_service, db_manager):
        """Test basic summary statistics."""
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
        stats = stats_service.get_summary_stats()
        
        assert stats["attempts"] == 4
        assert stats["audios_practiced"] == 2
        assert stats["avg_percentage"] > 0
        assert stats["avg_wer"] > 0

    def test_get_summary_stats_with_time_window(self, stats_service, db_manager):
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
            
            # Create attempts at different times
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
        since = datetime.now(UTC) - timedelta(days=5)
        stats = stats_service.get_summary_stats(since=since)
        
        assert stats["attempts"] == 1  # Only recent attempt
        assert stats["audios_practiced"] == 1

    def test_get_summary_stats_empty_database(self, stats_service):
        """Test summary statistics from empty database."""
        stats = stats_service.get_summary_stats()
        
        assert stats["attempts"] == 0
        assert stats["audios_practiced"] == 0
        assert stats["avg_percentage"] == 0.0
        assert stats["avg_wer"] == 0.0

    def test_get_summary_stats_invalid_time_window(self, stats_service):
        """Test summary statistics with invalid time window."""
        # since > until should be handled gracefully
        since = datetime.now(UTC)
        until = since - timedelta(days=1)
        
        # Should not raise exception, but may return empty results
        stats = stats_service.get_summary_stats(since=since, until=until)
        assert isinstance(stats, dict)

    def test_get_practice_log_basic(self, stats_service, db_manager):
        """Test basic practice log retrieval."""
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
        result = stats_service.get_practice_log()
        
        assert result["total"] == 2
        assert len(result["practice_log"]) == 2
        assert result["page"] == 1
        assert result["per_page"] == 20
        
        # Check item1 stats
        item1_log = next(log for log in result["practice_log"] if log["item_id"] == item1.id)
        assert item1_log["attempts_count"] == 3
        assert item1_log["avg_percentage"] > 80
        assert item1_log["best_percentage"] == 90

    def test_get_practice_log_with_pagination(self, stats_service, db_manager):
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
        result = stats_service.get_practice_log(page=2, per_page=10)
        
        assert result["total"] == 25
        assert result["page"] == 2
        assert result["per_page"] == 10
        assert result["total_pages"] == 3
        assert len(result["practice_log"]) == 10

    def test_get_practice_log_with_time_window(self, stats_service, db_manager):
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
        since = datetime.now(UTC) - timedelta(days=5)
        result = stats_service.get_practice_log(since=since)
        
        assert result["total"] == 1  # Only recent attempt
        assert len(result["practice_log"]) == 1

    def test_get_item_stats_success(self, stats_service, db_manager):
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
        stats = stats_service.get_item_stats(item.id)
        
        assert stats is not None
        assert stats["item_id"] == item.id
        assert stats["attempts_count"] == 3
        assert stats["avg_percentage"] > 80
        assert stats["best_percentage"] == 90
        assert stats["worst_percentage"] == 80
        assert stats["avg_wer"] > 0
        assert stats["best_wer"] < stats["worst_wer"]

    def test_get_item_stats_not_found(self, stats_service):
        """Test getting stats for non-existent item."""
        stats = stats_service.get_item_stats(999)
        assert stats is None

    def test_get_item_stats_no_attempts(self, stats_service, db_manager):
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
        stats = stats_service.get_item_stats(item.id)
        
        assert stats is not None
        assert stats["attempts_count"] == 0
        assert stats["avg_percentage"] == 0.0
        assert stats["best_percentage"] == 0
        assert stats["worst_percentage"] == 0

    def test_get_progress_over_time(self, stats_service, db_manager):
        """Test progress over time retrieval."""
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
        progress = stats_service.get_progress_over_time(item_id=item.id, days=10)
        
        assert len(progress) > 0
        for entry in progress:
            assert "date" in entry
            assert "attempts" in entry
            assert "avg_percentage" in entry
            assert "avg_wer" in entry

    def test_get_progress_over_time_all_items(self, stats_service, db_manager):
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
        progress = stats_service.get_progress_over_time(days=30)
        
        assert len(progress) > 0
        for entry in progress:
            assert "date" in entry
            assert "attempts" in entry

    def test_get_progress_over_time_empty_database(self, stats_service):
        """Test progress over time from empty database."""
        progress = stats_service.get_progress_over_time(days=30)
        
        assert len(progress) == 0

    def test_get_progress_over_time_custom_days(self, stats_service, db_manager):
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
        progress = stats_service.get_progress_over_time(item_id=item.id, days=5)
        
        assert len(progress) <= 5  # Should not exceed requested days

    def test_statistics_calculation_accuracy(self, stats_service, db_manager):
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
        stats = stats_service.get_item_stats(item.id)
        
        # Verify calculations
        assert stats["attempts_count"] == 3
        assert stats["avg_percentage"] == 80.0  # (80 + 90 + 70) / 3
        assert stats["best_percentage"] == 90
        assert stats["worst_percentage"] == 70
        assert abs(stats["avg_wer"] - 0.2) < 0.001  # (0.2 + 0.1 + 0.3) / 3
        assert stats["best_wer"] == 0.1
        assert stats["worst_wer"] == 0.3

    def test_edge_cases(self, stats_service, db_manager):
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
        stats = stats_service.get_item_stats(item.id)
        
        assert stats["avg_percentage"] == 100.0
        assert stats["avg_wer"] == 0.0
        assert stats["best_percentage"] == 100
        assert stats["worst_percentage"] == 100

    def test_time_window_edge_cases(self, stats_service):
        """Test time window edge cases."""
        # Test with same start and end time
        now = datetime.now(UTC)
        stats = stats_service.get_summary_stats(since=now, until=now)
        assert isinstance(stats, dict)
        
        # Test with None time values
        stats = stats_service.get_summary_stats(since=None, until=None)
        assert isinstance(stats, dict)
        
        # Test with future dates
        future = now + timedelta(days=1)
        stats = stats_service.get_summary_stats(since=future)
        assert isinstance(stats, dict)
