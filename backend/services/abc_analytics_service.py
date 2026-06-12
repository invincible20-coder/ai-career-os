"""
ABC Analytics Service — Full behavioral intelligence analytics engine.

Provides analytics endpoints for:
- Top successful patterns
- Pattern confidence distribution
- Preference evolution
- Career persona evolution
- Behavior trends
- Success trajectory
- Learning velocity
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.models.abc_intelligence import (
    ABCAnalyticsReport,
    PatternAnalytics,
    PersonaSnapshot,
    PersonaType,
    SelfEvaluationMetrics,
    TrendDirection,
)
from backend.storage.records import ABCLearningEventRecord, utc_now
from backend.storage.repository import HuntRepository


def _ensure_tz(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware (defaults to UTC)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@dataclass(slots=True)
class ABCAnalyticsService:
    """Full analytics engine for the Behavioral Intelligence Engine."""

    repository: HuntRepository

    async def build_report(self, user_id: str) -> ABCAnalyticsReport:
        """Build a full analytics report for a user."""
        now = utc_now()
        events = await self.repository.list_abc_learning_events(user_id, limit=1000)
        patterns = await self.repository.list_behavioral_patterns(user_id, limit=50)
        persona_record = await self.repository.get_career_persona(user_id)
        evaluations = await self.repository.list_self_evaluations(user_id, limit=100)

        top_patterns = self._top_successful_patterns(patterns)
        confidence_dist = self._pattern_confidence_distribution(patterns)
        pref_evolution = self._preference_evolution(events, now)
        persona_evolution = self._persona_evolution(persona_record)
        behavior_trends = self._behavior_trends(events, now)
        success_trajectory = self._success_trajectory(events, now)
        learning_velocity = self._learning_velocity(events, now)
        self_eval = self._self_evaluation_metrics(user_id, evaluations, now)

        return ABCAnalyticsReport(
            user_id=user_id,
            top_successful_patterns=top_patterns,
            pattern_confidence_distribution=confidence_dist,
            preference_evolution=pref_evolution,
            persona_evolution=persona_evolution,
            behavior_trends=behavior_trends,
            success_trajectory=success_trajectory,
            learning_velocity=learning_velocity,
            self_evaluation=self_eval,
            updated_at=now,
        )

    async def top_successful_patterns(
        self, user_id: str, *, limit: int = 10
    ) -> list[PatternAnalytics]:
        """Return patterns with highest interview/offer rates."""
        patterns = await self.repository.list_behavioral_patterns(
            user_id, min_confidence=0.2, limit=limit
        )
        return self._top_successful_patterns(patterns)

    async def learning_velocity(self, user_id: str) -> float:
        """How fast the engine improves its predictions."""
        events = await self.repository.list_abc_learning_events(user_id, limit=500)
        return self._learning_velocity(events, utc_now())

    @staticmethod
    def _top_successful_patterns(patterns) -> list[PatternAnalytics]:
        result = []
        for p in patterns:
            total = max(1, p.occurrences)
            positive = p.interviews + p.offers * 2 + p.acceptances * 3
            success_rate = round(min(1.0, positive / total), 4)
            result.append(
                PatternAnalytics(
                    pattern_id=p.id,
                    antecedent_signature=p.antecedent_signature,
                    occurrences=p.occurrences,
                    success_rate=success_rate,
                    confidence=p.confidence_score,
                    trend=TrendDirection(p.trend_direction),
                )
            )
        result.sort(key=lambda x: x.success_rate, reverse=True)
        return result[:10]

    @staticmethod
    def _pattern_confidence_distribution(patterns) -> dict[str, int]:
        """Bucket patterns by confidence level."""
        buckets: dict[str, int] = {
            "very_low": 0,    # 0.0 - 0.2
            "low": 0,         # 0.2 - 0.4
            "medium": 0,      # 0.4 - 0.6
            "high": 0,        # 0.6 - 0.8
            "very_high": 0,   # 0.8 - 1.0
        }
        for p in patterns:
            c = p.confidence_score
            if c < 0.2:
                buckets["very_low"] += 1
            elif c < 0.4:
                buckets["low"] += 1
            elif c < 0.6:
                buckets["medium"] += 1
            elif c < 0.8:
                buckets["high"] += 1
            else:
                buckets["very_high"] += 1
        return buckets

    @staticmethod
    def _preference_evolution(
        events: list[ABCLearningEventRecord],
        now: datetime,
    ) -> list[dict[str, Any]]:
        """Track how category weights changed over time (weekly snapshots)."""
        if not events:
            return []

        # Group events by week
        weeks: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for event in events:
            week_num = int((now - _ensure_tz(event.timestamp)).total_seconds() / (7 * 86400))
            category = event.job_category
            weeks[week_num][category] += event.consequence_weight

        snapshots = []
        for week_num in sorted(weeks.keys(), reverse=True)[:12]:  # last 12 weeks
            week_data = dict(weeks[week_num])
            total = sum(week_data.values()) or 1.0
            normalized = {
                cat: round(val / total, 4) for cat, val in week_data.items()
            }
            snapshots.append({
                "weeks_ago": week_num,
                "category_weights": normalized,
            })
        return snapshots

    @staticmethod
    def _persona_evolution(persona_record) -> list[PersonaSnapshot]:
        if persona_record is None:
            return []
        return [
            PersonaSnapshot(**snap) for snap in persona_record.evolution_history_json
        ]

    @staticmethod
    def _behavior_trends(
        events: list[ABCLearningEventRecord],
        now: datetime,
    ) -> dict[str, TrendDirection]:
        """Determine rising/falling/stable for each category."""
        if not events:
            return {}

        cutoff = now - timedelta(days=30)
        category_recent: dict[str, int] = defaultdict(int)
        category_total: dict[str, int] = defaultdict(int)

        for event in events:
            category_total[event.job_category] += 1
            if _ensure_tz(event.timestamp) >= cutoff:
                category_recent[event.job_category] += 1

        total_days = max(
            1.0,
            (now - _ensure_tz(min(e.timestamp for e in events))).total_seconds() / 86400,
        )
        trends: dict[str, TrendDirection] = {}
        for category, total in category_total.items():
            recent = category_recent.get(category, 0)
            recent_rate = recent / 30
            overall_rate = total / total_days
            if recent_rate > overall_rate * 1.3:
                trends[category] = TrendDirection.RISING
            elif recent_rate < overall_rate * 0.7:
                trends[category] = TrendDirection.FALLING
            else:
                trends[category] = TrendDirection.STABLE
        return trends

    @staticmethod
    def _success_trajectory(
        events: list[ABCLearningEventRecord],
        now: datetime,
    ) -> list[dict[str, float]]:
        """Interview/offer rate over rolling time windows."""
        if not events:
            return []

        windows = [7, 14, 30, 60, 90]
        trajectory = []
        for window in windows:
            cutoff = now - timedelta(days=window)
            window_events = [e for e in events if _ensure_tz(e.timestamp) >= cutoff]
            total = len(window_events)
            if total == 0:
                continue
            interviews = sum(
                1 for e in window_events
                if e.consequence_level in ("interview", "final_round")
            )
            offers = sum(
                1 for e in window_events
                if e.consequence_level in ("offer", "accepted")
            )
            trajectory.append({
                "window_days": float(window),
                "total_events": float(total),
                "interview_rate": round(interviews / total, 4),
                "offer_rate": round(offers / total, 4),
            })
        return trajectory

    @staticmethod
    def _learning_velocity(
        events: list[ABCLearningEventRecord],
        now: datetime,
    ) -> float:
        """How fast the engine improves — measured by recent vs older outcome quality."""
        if len(events) < 10:
            return 0.0

        mid = len(events) // 2
        older = events[:mid]
        recent = events[mid:]

        def avg_weight(evts):
            if not evts:
                return 0.0
            return sum(e.consequence_weight for e in evts) / len(evts)

        older_quality = avg_weight(older)
        recent_quality = avg_weight(recent)

        if older_quality <= 0:
            return round(min(1.0, recent_quality), 4)

        velocity = (recent_quality - older_quality) / older_quality
        return round(max(-1.0, min(1.0, velocity)), 4)

    @staticmethod
    def _self_evaluation_metrics(
        user_id: str,
        evaluations,
        now: datetime,
    ) -> SelfEvaluationMetrics | None:
        if not evaluations:
            return None

        total = len(evaluations)
        evaluated = [e for e in evaluations if e.was_correct is not None]
        correct = sum(1 for e in evaluated if e.was_correct)

        return SelfEvaluationMetrics(
            user_id=user_id,
            total_predictions=total,
            correct_predictions=correct,
            pattern_accuracy=round(correct / max(1, len(evaluated)), 4),
            confidence_calibration=round(
                sum(e.predicted_confidence for e in evaluated) / max(1, len(evaluated)),
                4,
            ),
            updated_at=now,
        )
