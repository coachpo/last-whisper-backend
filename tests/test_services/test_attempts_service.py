"""Tests for AttemptsService."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, UTC

from app.services.attempts_service import AttemptsService
from app.models.database import Attempt, Item


class TestAttemptsService:
    """Test cases for AttemptsService."""

    @pytest.fixture
    def attempts_service(self, db_manager):
        """Create an attempts service instance for testing."""
        return AttemptsService(db_manager)

    def test_init(self, db_manager):
        """Test service initialization."""
        service = AttemptsService(db_manager)
        assert service.db_manager == db_manager

    def test_create_attempt_success(self, attempts_service, db_manager):
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
        user_text = "Hei, tämä on testi!"
        attempt = attempts_service.create_attempt(item_id, user_text)
        
        assert attempt is not None
        assert attempt.item_id == item_id
        assert attempt.text == user_text
        assert attempt.percentage >= 0
        assert attempt.wer >= 0.0
        assert attempt.words_ref > 0
        assert attempt.words_correct >= 0

    def test_create_attempt_item_not_found(self, attempts_service):
        """Test attempt creation with non-existent item."""
        attempt = attempts_service.create_attempt(999, "Test text")
        assert attempt is None

    def test_create_attempt_empty_user_text(self, attempts_service, db_manager):
        """Test attempt creation with empty user text."""
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
        attempt = attempts_service.create_attempt(item_id, "")
        
        assert attempt is not None
        assert attempt.percentage == 0  # Should score 0 for empty text

    def test_get_attempt_success(self, attempts_service, db_manager):
        """Test getting attempt by ID."""
        # Create an item and attempt
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
        retrieved_attempt = attempts_service.get_attempt(attempt_id)
        
        assert retrieved_attempt is not None
        assert retrieved_attempt.id == attempt_id
        assert retrieved_attempt.text == "User attempt"

    def test_get_attempt_not_found(self, attempts_service):
        """Test getting non-existent attempt."""
        attempt = attempts_service.get_attempt(999)
        assert attempt is None

    def test_list_attempts_basic(self, attempts_service, db_manager):
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
                    percentage=70 + i * 10,
                    wer=0.3 - i * 0.1,
                    words_ref=5,
                    words_correct=4 - i
                )
                session.add(attempt)
            session.commit()
        
        # List attempts
        result = attempts_service.list_attempts()
        
        assert result["total"] == 3
        assert len(result["attempts"]) == 3
        assert result["page"] == 1
        assert result["per_page"] == 20
        assert result["total_pages"] == 1

    def test_list_attempts_with_filters(self, attempts_service, db_manager):
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
                    percentage=80 + i * 10,
                    wer=0.2 - i * 0.1,
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
        result = attempts_service.list_attempts(item_id=item1.id)
        assert result["total"] == 2
        assert all(attempt["item_id"] == item1.id for attempt in result["attempts"])

    def test_list_attempts_with_pagination(self, attempts_service, db_manager):
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
        result = attempts_service.list_attempts(page=2, per_page=10)
        
        assert result["total"] == 25
        assert result["page"] == 2
        assert result["per_page"] == 10
        assert result["total_pages"] == 3
        assert len(result["attempts"]) == 10

    def test_calculate_score_perfect_match(self, attempts_service):
        """Test score calculation with perfect match."""
        reference = "Hei, tämä on testi!"
        hypothesis = "Hei, tämä on testi!"
        
        score = attempts_service._calculate_score(reference, hypothesis)
        
        assert score["wer"] == 0.0
        assert score["percentage"] == 100
        assert score["words_ref"] == 4
        assert score["words_correct"] == 4

    def test_calculate_score_partial_match(self, attempts_service):
        """Test score calculation with partial match."""
        reference = "Hei, tämä on testi!"
        hypothesis = "Hei, tämä testi!"
        
        score = attempts_service._calculate_score(reference, hypothesis)
        
        assert score["wer"] > 0.0
        assert score["wer"] < 1.0
        assert score["percentage"] < 100
        assert score["percentage"] > 0
        assert score["words_ref"] == 4
        assert score["words_correct"] < 4

    def test_calculate_score_no_match(self, attempts_service):
        """Test score calculation with no match."""
        reference = "Hei, tämä on testi!"
        hypothesis = "Täysin eri teksti"
        
        score = attempts_service._calculate_score(reference, hypothesis)
        
        assert score["wer"] > 0.0
        assert score["percentage"] == 0
        assert score["words_ref"] == 4
        assert score["words_correct"] == 0

    def test_calculate_score_empty_reference(self, attempts_service):
        """Test score calculation with empty reference."""
        reference = ""
        hypothesis = "Some text"
        
        score = attempts_service._calculate_score(reference, hypothesis)
        
        assert score["wer"] == 1.0
        assert score["percentage"] == 0
        assert score["words_ref"] == 0
        assert score["words_correct"] == 0

    def test_calculate_score_empty_hypothesis(self, attempts_service):
        """Test score calculation with empty hypothesis."""
        reference = "Hei, tämä on testi!"
        hypothesis = ""
        
        score = attempts_service._calculate_score(reference, hypothesis)
        
        assert score["wer"] == 1.0
        assert score["percentage"] == 0
        assert score["words_ref"] == 4
        assert score["words_correct"] == 0

    def test_normalize_text(self, attempts_service):
        """Test text normalization."""
        text = "Hei, TÄMÄ on testi!!!"
        normalized = attempts_service._normalize_text(text)
        
        # Should be lowercase and without punctuation
        assert normalized == "hei tama on testi"
        assert "!" not in normalized
        assert "TÄMÄ" not in normalized

    def test_normalize_text_with_accents(self, attempts_service):
        """Test text normalization with accented characters."""
        text = "Héllö, wörld!"
        normalized = attempts_service._normalize_text(text)
        
        # Should handle accented characters
        assert "é" not in normalized
        assert "ö" not in normalized

    def test_tokenize_words(self, attempts_service):
        """Test word tokenization."""
        text = "Hei, tämä on testi!"
        words = attempts_service._tokenize_words(text)
        
        expected = ["hei", "tama", "on", "testi"]
        assert words == expected

    def test_tokenize_words_empty(self, attempts_service):
        """Test word tokenization with empty text."""
        words = attempts_service._tokenize_words("")
        assert words == []
        
        words = attempts_service._tokenize_words("   ")
        assert words == []

    def test_attempt_to_dict(self, attempts_service):
        """Test converting attempt to dictionary."""
        attempt = Mock()
        attempt.id = 1
        attempt.item_id = 2
        attempt.text = "Test attempt"
        attempt.percentage = 85
        attempt.wer = 0.15
        attempt.words_ref = 5
        attempt.words_correct = 4
        attempt.created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        
        result = attempts_service._attempt_to_dict(attempt)
        
        assert result["id"] == 1
        assert result["item_id"] == 2
        assert result["text"] == "Test attempt"
        assert result["percentage"] == 85
        assert result["wer"] == 0.15
        assert result["words_ref"] == 5
        assert result["words_correct"] == 4
        assert result["created_at"] == "2024-01-01T12:00:00+00:00"

    @patch('app.services.attempts_service.HAS_JIWER', True)
    @patch('app.services.attempts_service.wer')
    def test_calculate_score_with_jiwer(self, mock_wer, attempts_service):
        """Test score calculation using jiwer library."""
        mock_wer.return_value = 0.25
        
        reference = "Hei, tämä on testi!"
        hypothesis = "Hei, tämä testi!"
        
        score = attempts_service._calculate_score(reference, hypothesis)
        
        mock_wer.assert_called_once()
        assert score["wer"] == 0.25
        assert score["percentage"] == 75  # (1 - 0.25) * 100

    @patch('app.services.attempts_service.HAS_JIWER', False)
    def test_calculate_score_without_jiwer(self, attempts_service):
        """Test score calculation without jiwer library."""
        reference = "Hei, tämä on testi!"
        hypothesis = "Hei, tämä testi!"
        
        score = attempts_service._calculate_score(reference, hypothesis)
        
        # Should use manual calculation
        assert score["wer"] >= 0.0
        assert score["wer"] <= 1.0
        assert score["percentage"] >= 0
        assert score["percentage"] <= 100

    def test_manual_wer_calculation(self, attempts_service):
        """Test manual WER calculation."""
        ref_words = ["hei", "tama", "on", "testi"]
        hyp_words = ["hei", "testi"]
        
        wer_score, words_correct = attempts_service._calculate_wer_manual(ref_words, hyp_words)
        
        assert wer_score == 0.5  # 2 errors out of 4 words
        assert words_correct == 2  # 2 correct words

    def test_manual_wer_calculation_empty_reference(self, attempts_service):
        """Test manual WER calculation with empty reference."""
        ref_words = []
        hyp_words = ["hei", "testi"]
        
        wer_score, words_correct = attempts_service._calculate_wer_manual(ref_words, hyp_words)
        
        assert wer_score == 1.0  # 100% error rate
        assert words_correct == 0
