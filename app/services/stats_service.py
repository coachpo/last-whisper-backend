"""Stats service for aggregating practice statistics."""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from sqlalchemy import func, distinct

from app.models.database import DatabaseManager, Attempt, Item


class StatsService:
    """Service for aggregating dictation statistics."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def get_summary_stats(
            self,
            since: Optional[datetime] = None,
            until: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get summary statistics for the specified time window."""
        with self.db_manager.get_session() as session:
            # Base query for attempts in time window
            query = session.query(Attempt)

            if since:
                query = query.filter(Attempt.created_at >= since)
            if until:
                query = query.filter(Attempt.created_at <= until)

            # Get total attempts
            attempts_count = query.count()

            if attempts_count == 0:
                return {
                    "attempts": 0,
                    "audios_practiced": 0,
                    "avg_percentage": 0.0,
                    "avg_wer": 0.0,
                }

            # Get unique audio items practiced
            audios_practiced = (
                query.with_entities(distinct(Attempt.item_id))
                .count()
            )

            # Get average percentage and WER
            stats = (
                query.with_entities(
                    func.avg(Attempt.percentage).label("avg_percentage"),
                    func.avg(Attempt.wer).label("avg_wer"),
                )
                .first()
            )

            return {
                "attempts": attempts_count,
                "audios_practiced": audios_practiced,
                "avg_percentage": round(float(stats.avg_percentage or 0), 2),
                "avg_wer": round(float(stats.avg_wer or 0), 4),
            }

    def get_practice_log(
            self,
            since: Optional[datetime] = None,
            until: Optional[datetime] = None,
            page: int = 1,
            per_page: int = 20,
    ) -> Dict[str, Any]:
        """Get per-audio practice log with aggregated statistics."""
        with self.db_manager.get_session() as session:
            # Subquery for attempts in time window
            attempts_subq = session.query(Attempt)

            if since:
                attempts_subq = attempts_subq.filter(Attempt.created_at >= since)
            if until:
                attempts_subq = attempts_subq.filter(Attempt.created_at <= until)

            attempts_subq = attempts_subq.subquery()

            # Main query: aggregate stats per item
            query = (
                session.query(
                    Item.id.label("item_id"),
                    Item.text,
                    func.count(attempts_subq.c.id).label("attempts_count"),
                    func.min(attempts_subq.c.created_at).label("first_attempt_at"),
                    func.max(attempts_subq.c.created_at).label("last_attempt_at"),
                    func.avg(attempts_subq.c.percentage).label("avg_percentage"),
                    func.max(attempts_subq.c.percentage).label("best_percentage"),
                    func.avg(attempts_subq.c.wer).label("avg_wer"),
                )
                .outerjoin(attempts_subq, Item.id == attempts_subq.c.item_id)
                .filter(attempts_subq.c.id.isnot(None))  # Only items with attempts
                .group_by(Item.id, Item.text)
                .order_by(func.max(attempts_subq.c.created_at).desc())  # Most recently practiced first
            )

            # Get total count before pagination
            total = query.count()

            # Apply pagination
            offset = (page - 1) * per_page
            results = query.offset(offset).limit(per_page).all()

            # Format results
            practice_log = []
            for result in results:
                practice_log.append({
                    "item_id": result.item_id,
                    "text": result.text,
                    "attempts_count": result.attempts_count,
                    "first_attempt_at": result.first_attempt_at.isoformat() if result.first_attempt_at else None,
                    "last_attempt_at": result.last_attempt_at.isoformat() if result.last_attempt_at else None,
                    "avg_percentage": round(float(result.avg_percentage or 0), 2),
                    "best_percentage": result.best_percentage or 0,
                    "avg_wer": round(float(result.avg_wer or 0), 4),
                })

            return {
                "practice_log": practice_log,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": (total + per_page - 1) // per_page,
            }

    def get_item_stats(self, item_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed statistics for a specific item."""
        with self.db_manager.get_session() as session:
            # Get the item
            item = session.query(Item).filter(Item.id == item_id).first()
            if not item:
                return None

            # Get attempt statistics
            attempts_query = session.query(Attempt).filter(Attempt.item_id == item_id)
            attempts_count = attempts_query.count()

            if attempts_count == 0:
                return {
                    "item_id": item_id,
                    "text": item.text,
                    "attempts_count": 0,
                    "first_attempt_at": None,
                    "last_attempt_at": None,
                    "avg_percentage": 0.0,
                    "best_percentage": 0,
                    "worst_percentage": 0,
                    "avg_wer": 0.0,
                    "best_wer": 0.0,
                    "worst_wer": 0.0,
                }

            # Get aggregated stats
            stats = (
                attempts_query.with_entities(
                    func.min(Attempt.created_at).label("first_attempt_at"),
                    func.max(Attempt.created_at).label("last_attempt_at"),
                    func.avg(Attempt.percentage).label("avg_percentage"),
                    func.max(Attempt.percentage).label("best_percentage"),
                    func.min(Attempt.percentage).label("worst_percentage"),
                    func.avg(Attempt.wer).label("avg_wer"),
                    func.min(Attempt.wer).label("best_wer"),
                    func.max(Attempt.wer).label("worst_wer"),
                )
                .first()
            )

            return {
                "item_id": item_id,
                "text": item.text,
                "attempts_count": attempts_count,
                "first_attempt_at": stats.first_attempt_at.isoformat() if stats.first_attempt_at else None,
                "last_attempt_at": stats.last_attempt_at.isoformat() if stats.last_attempt_at else None,
                "avg_percentage": round(float(stats.avg_percentage or 0), 2),
                "best_percentage": stats.best_percentage or 0,
                "worst_percentage": stats.worst_percentage or 0,
                "avg_wer": round(float(stats.avg_wer or 0), 4),
                "best_wer": stats.best_wer or 0.0,
                "worst_wer": stats.worst_wer or 0.0,
            }

    def get_progress_over_time(
            self,
            item_id: Optional[int] = None,
            days: int = 30,
    ) -> List[Dict[str, Any]]:
        """Get progress over time (daily aggregations)."""
        with self.db_manager.get_session() as session:
            # Calculate date range
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days - 1)

            # Base query
            query = session.query(
                func.date(Attempt.created_at).label("date"),
                func.count(Attempt.id).label("attempts"),
                func.avg(Attempt.percentage).label("avg_percentage"),
                func.avg(Attempt.wer).label("avg_wer"),
            ).filter(
                func.date(Attempt.created_at) >= start_date
            )

            if item_id:
                query = query.filter(Attempt.item_id == item_id)

            # Group by date
            results = (
                query.group_by(func.date(Attempt.created_at))
                .order_by(func.date(Attempt.created_at))
                .all()
            )

            # Format results
            progress = []
            for result in results:
                progress.append({
                    "date": result.date.isoformat(),
                    "attempts": result.attempts,
                    "avg_percentage": round(float(result.avg_percentage or 0), 2),
                    "avg_wer": round(float(result.avg_wer or 0), 4),
                })

            return progress
