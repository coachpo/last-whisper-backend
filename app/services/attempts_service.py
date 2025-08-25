"""Attempts service for managing dictation attempts and scoring."""

import re
import unicodedata
from datetime import datetime
from typing import Optional, Dict, Any, List

try:
    from jiwer import wer, cer

    HAS_JIWER = True
except ImportError:
    HAS_JIWER = False

try:
    from unidecode import unidecode

    HAS_UNIDECODE = True
except ImportError:
    HAS_UNIDECODE = False

from app.models.database import DatabaseManager, Attempt, Item


class AttemptsService:
    """Service for managing dictation attempts and scoring."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def create_attempt(
            self,
            item_id: int,
            user_text: str,
    ) -> Optional[Attempt]:
        """Create a new attempt with automatic scoring."""
        with self.db_manager.get_session() as session:
            # Get the item
            item = session.query(Item).filter(Item.id == item_id).first()
            if not item:
                return None

            # Calculate score
            score_result = self._calculate_score(item.text, user_text)

            # Create attempt
            attempt = Attempt(
                item_id=item_id,
                text=user_text,
                percentage=score_result["percentage"],
                wer=score_result["wer"],
                words_ref=score_result["words_ref"],
                words_correct=score_result["words_correct"],
            )

            session.add(attempt)
            session.commit()
            session.refresh(attempt)

            return attempt

    def get_attempt(self, attempt_id: int) -> Optional[Attempt]:
        """Get an attempt by ID."""
        with self.db_manager.get_session() as session:
            return session.query(Attempt).filter(Attempt.id == attempt_id).first()

    def list_attempts(
            self,
            item_id: Optional[int] = None,
            since: Optional[datetime] = None,
            until: Optional[datetime] = None,
            page: int = 1,
            per_page: int = 20,
    ) -> Dict[str, Any]:
        """List attempts with filtering and pagination."""
        with self.db_manager.get_session() as session:
            # Start with base query
            query = session.query(Attempt)

            # Apply filters
            if item_id:
                query = query.filter(Attempt.item_id == item_id)

            if since:
                query = query.filter(Attempt.created_at >= since)

            if until:
                query = query.filter(Attempt.created_at <= until)

            # Order by creation time (newest first)
            query = query.order_by(Attempt.created_at.desc())

            # Get total count before pagination
            total = query.count()

            # Apply pagination
            offset = (page - 1) * per_page
            attempts = query.offset(offset).limit(per_page).all()

            # Build response
            return {
                "attempts": [self._attempt_to_dict(attempt) for attempt in attempts],
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": (total + per_page - 1) // per_page,
            }

    def _calculate_score(self, reference_text: str, hypothesis_text: str) -> Dict[str, Any]:
        """Calculate WER and percentage score between reference and hypothesis."""
        # Normalize both texts
        ref_normalized = self._normalize_text(reference_text)
        hyp_normalized = self._normalize_text(hypothesis_text)

        # Tokenize into words
        ref_words = self._tokenize_words(ref_normalized)
        hyp_words = self._tokenize_words(hyp_normalized)

        words_ref = len(ref_words)

        if words_ref == 0:
            # Handle edge case of empty reference
            return {
                "wer": 1.0 if len(hyp_words) > 0 else 0.0,
                "percentage": 0 if len(hyp_words) > 0 else 100,
                "words_ref": 0,
                "words_correct": 0,
            }

        # Calculate WER using library if available
        if HAS_JIWER:
            try:
                wer_score = wer(ref_words, hyp_words)
                # Calculate words correct from WER
                # WER = (S + D + I) / N, where S=substitutions, D=deletions, I=insertions, N=reference length
                # Approximation: words_correct ≈ N * (1 - WER)
                words_correct = max(0, int(words_ref * (1 - wer_score)))
            except Exception:
                # Fallback to manual calculation
                wer_score, words_correct = self._calculate_wer_manual(ref_words, hyp_words)
        else:
            # Manual WER calculation
            wer_score, words_correct = self._calculate_wer_manual(ref_words, hyp_words)

        # Calculate percentage (0-100)
        percentage = max(0, min(100, int((words_correct / words_ref) * 100)))

        return {
            "wer": min(1.0, max(0.0, wer_score)),  # Clamp to [0, 1]
            "percentage": percentage,
            "words_ref": words_ref,
            "words_correct": words_correct,
        }

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        if not text:
            return ""

        # Convert to lowercase
        text = text.lower()

        # Normalize Unicode (decompose accented characters)
        text = unicodedata.normalize('NFD', text)

        # Remove diacritics if unidecode is available
        if HAS_UNIDECODE:
            text = unidecode(text)

        # Remove punctuation (but keep apostrophes) and extra whitespace
        text = re.sub(r'[^\w\s\']', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()

        return text

    def _tokenize_words(self, text: str) -> List[str]:
        """Tokenize text into words."""
        if not text:
            return []

        # Simple whitespace tokenization after normalization
        words = text.split()
        return [word.lower() for word in words if word]  # Remove empty strings and convert to lowercase

    def _calculate_wer_manual(self, ref_words: List[str], hyp_words: List[str]) -> tuple[float, int]:
        """Manual WER calculation using edit distance."""
        if not ref_words:
            return (1.0 if hyp_words else 0.0), 0

        # Calculate edit distance matrix
        m, n = len(ref_words), len(hyp_words)
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        # Initialize base cases
        for i in range(m + 1):
            dp[i][0] = i  # Deletions
        for j in range(n + 1):
            dp[0][j] = j  # Insertions

        # Fill the matrix
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if ref_words[i - 1] == hyp_words[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1]  # Match
                else:
                    dp[i][j] = 1 + min(
                        dp[i - 1][j],  # Deletion
                        dp[i][j - 1],  # Insertion
                        dp[i - 1][j - 1]  # Substitution
                    )

        # Calculate WER and words correct
        edit_distance = dp[m][n]
        wer_score = edit_distance / len(ref_words)
        words_correct = max(0, len(ref_words) - edit_distance)

        return wer_score, words_correct

    def _attempt_to_dict(self, attempt: Attempt) -> Dict[str, Any]:
        """Convert Attempt model to dictionary."""
        return {
            "id": attempt.id,
            "item_id": attempt.item_id,
            "text": attempt.text,
            "percentage": attempt.percentage,
            "wer": attempt.wer,
            "words_ref": attempt.words_ref,
            "words_correct": attempt.words_correct,
            "created_at": attempt.created_at.isoformat() if attempt.created_at else None,
        }
