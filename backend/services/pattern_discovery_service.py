"""
Behavioral Pattern Discovery Engine.

Analyzes ABC learning events for recurring antecedent signatures.
Discovers patterns like "Remote + Python + Startup" and tracks their
outcome statistics, confidence scores, and trend direction.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from backend.models.abc_intelligence import (
    BehavioralPattern,
    ConsequenceLevel,
    TrendDirection,
    consequence_weight_for,
)
from backend.storage.records import ABCLearningEventRecord, utc_now
from backend.storage.repository import HuntRepository

_MIN_OCCURRENCES_FOR_CONFIDENCE = 3
_TREND_WINDOW_DAYS = 30


@dataclass(slots=True)
class PatternDiscoveryService:
    """Discover recurring successful patterns from ABC event history."""

    repository: HuntRepository

    async def discover_patterns(self, user_id: str) -> list[BehavioralPattern]:
        """Analyze all learning events and discover/update behavioral patterns."""
        events = await self.repository.list_abc_learning_events(user_id, limit=1000)
        if not events:
            return []

        signature_events: dict[str, list[ABCLearningEventRecord]] = defaultdict(list)
        for event in events:
            signature = event.antecedent_signature or self._build_signature(event)
            if signature:
                signature_events[signature].append(event)

        patterns: list[BehavioralPattern] = []
        now = utc_now()

        for signature, sig_events in signature_events.items():
            existing = await self.repository.get_behavioral_pattern(user_id, signature)
            pattern_id = existing.id if existing else str(uuid.uuid4())

            stats = self._compute_stats(sig_events)
            confidence = self._compute_confidence(stats, len(sig_events))
            trend = self._compute_trend(sig_events, now)

            await self.repository.upsert_behavioral_pattern(
                pattern_id=pattern_id,
                user_id=user_id,
                antecedent_signature=signature,
                antecedent_embedding=[],  # populated by SemanticService
                occurrences=len(sig_events),
                views=stats["views"],
                clicks=stats["clicks"],
                saves=stats["saves"],
                applies=stats["applies"],
                assessments=stats["assessments"],
                interviews=stats["interviews"],
                final_rounds=stats["final_rounds"],
                offers=stats["offers"],
                rejections=stats["rejections"],
                acceptances=stats["acceptances"],
                confidence_score=confidence,
                trend_direction=trend.value,
            )

            last_event = max(sig_events, key=lambda e: e.timestamp)
            patterns.append(
                BehavioralPattern(
                    pattern_id=pattern_id,
                    user_id=user_id,
                    antecedent_signature=signature,
                    occurrences=len(sig_events),
                    views=stats["views"],
                    clicks=stats["clicks"],
                    saves=stats["saves"],
                    applies=stats["applies"],
                    assessments=stats["assessments"],
                    interviews=stats["interviews"],
                    final_rounds=stats["final_rounds"],
                    offers=stats["offers"],
                    rejections=stats["rejections"],
                    acceptances=stats["acceptances"],
                    confidence_score=confidence,
                    last_seen=last_event.timestamp,
                    trend_direction=trend,
                    created_at=existing.created_at if existing else now,
                )
            )

        return sorted(patterns, key=lambda p: p.confidence_score, reverse=True)

    async def get_top_patterns(
        self,
        user_id: str,
        *,
        min_confidence: float = 0.3,
        limit: int = 10,
    ) -> list[BehavioralPattern]:
        """Return highest-confidence patterns for a user."""
        records = await self.repository.list_behavioral_patterns(
            user_id, min_confidence=min_confidence, limit=limit,
        )
        now = utc_now()
        return [
            BehavioralPattern(
                pattern_id=r.id,
                user_id=r.user_id,
                antecedent_signature=r.antecedent_signature,
                antecedent_embedding=r.antecedent_embedding_json,
                occurrences=r.occurrences,
                views=r.views,
                clicks=r.clicks,
                saves=r.saves,
                applies=r.applies,
                assessments=r.assessments,
                interviews=r.interviews,
                final_rounds=r.final_rounds,
                offers=r.offers,
                rejections=r.rejections,
                acceptances=r.acceptances,
                confidence_score=r.confidence_score,
                last_seen=r.last_seen,
                trend_direction=TrendDirection(r.trend_direction),
                created_at=r.created_at,
            )
            for r in records
        ]

    def pattern_score_for_job(
        self,
        patterns: list[BehavioralPattern],
        job_category: str,
        job_signature: str,
    ) -> float:
        """Compute how well a job matches known successful patterns."""
        if not patterns:
            return 0.0

        best_score = 0.0
        for pattern in patterns:
            sig_lower = pattern.antecedent_signature.lower()
            job_sig_lower = job_signature.lower()
            # Check for overlapping terms
            sig_terms = set(sig_lower.split())
            job_terms = set(job_sig_lower.split())
            if not sig_terms:
                continue
            overlap = len(sig_terms & job_terms) / len(sig_terms)
            if overlap > 0:
                success_rate = self._pattern_success_rate(pattern)
                score = overlap * success_rate * pattern.confidence_score
                best_score = max(best_score, score)

        return round(min(1.0, best_score), 4)

    @staticmethod
    def _build_signature(event: ABCLearningEventRecord) -> str:
        """Build a signature from event fields when none exists."""
        parts = []
        if event.job_location and event.job_location.strip():
            loc = event.job_location.strip().lower()
            if "remote" in loc:
                parts.append("remote")
            else:
                parts.append(loc.split(",")[0].strip())
        if event.job_category:
            parts.append(event.job_category)
        # Extract key requirements
        if event.job_requirements_json:
            for req in event.job_requirements_json[:3]:
                parts.append(req.lower().strip())
        return " + ".join(parts) if parts else ""

    @staticmethod
    def _compute_stats(events: list[ABCLearningEventRecord]) -> dict[str, int]:
        """Aggregate outcome counts from events."""
        stats: dict[str, int] = defaultdict(int)
        for event in events:
            level = event.consequence_level
            if level == ConsequenceLevel.VIEWED.value:
                stats["views"] += 1
            elif level == ConsequenceLevel.CLICKED.value:
                stats["clicks"] += 1
            elif level == ConsequenceLevel.SAVED.value:
                stats["saves"] += 1
            elif level == ConsequenceLevel.APPLIED.value:
                stats["applies"] += 1
            elif level == ConsequenceLevel.ASSESSMENT.value:
                stats["assessments"] += 1
            elif level == ConsequenceLevel.INTERVIEW.value:
                stats["interviews"] += 1
            elif level == ConsequenceLevel.FINAL_ROUND.value:
                stats["final_rounds"] += 1
            elif level == ConsequenceLevel.OFFER.value:
                stats["offers"] += 1
            elif level == ConsequenceLevel.ACCEPTED.value:
                stats["acceptances"] += 1
            else:
                stats["rejections"] += 1
        return dict(stats)

    @staticmethod
    def _compute_confidence(stats: dict[str, int], total: int) -> float:
        """Compute pattern confidence from sample size and outcome quality."""
        if total < _MIN_OCCURRENCES_FOR_CONFIDENCE:
            return round(total / (_MIN_OCCURRENCES_FOR_CONFIDENCE * 2), 4)

        positive = (
            stats.get("interviews", 0)
            + stats.get("offers", 0) * 2
            + stats.get("acceptances", 0) * 3
            + stats.get("final_rounds", 0) * 1.5
            + stats.get("assessments", 0) * 0.5
        )
        negative = stats.get("rejections", 0)
        success_quality = positive / max(1, positive + negative)
        volume_factor = min(1.0, total / 20)
        return round(min(1.0, success_quality * 0.70 + volume_factor * 0.30), 4)

    @staticmethod
    def _compute_trend(
        events: list[ABCLearningEventRecord],
        now: datetime,
    ) -> TrendDirection:
        """Determine if a pattern is rising, stable, or falling."""
        cutoff = now - timedelta(days=_TREND_WINDOW_DAYS)
        recent = [e for e in events if e.timestamp >= cutoff]
        older = [e for e in events if e.timestamp < cutoff]

        if not older:
            return TrendDirection.RISING if len(recent) >= 2 else TrendDirection.STABLE

        recent_rate = len(recent) / _TREND_WINDOW_DAYS
        total_days = max(1.0, (now - min(e.timestamp for e in events)).total_seconds() / 86400)
        overall_rate = len(events) / total_days

        if recent_rate > overall_rate * 1.3:
            return TrendDirection.RISING
        if recent_rate < overall_rate * 0.7:
            return TrendDirection.FALLING
        return TrendDirection.STABLE

    @staticmethod
    def _pattern_success_rate(pattern: BehavioralPattern) -> float:
        """Compute weighted success rate for a pattern."""
        positive = (
            pattern.interviews * 0.6
            + pattern.offers * 0.9
            + pattern.acceptances * 1.0
            + pattern.final_rounds * 0.75
            + pattern.assessments * 0.4
        )
        total = max(1, pattern.occurrences)
        return min(1.0, positive / total)
