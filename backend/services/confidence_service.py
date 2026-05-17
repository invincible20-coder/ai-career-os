"""
Confidence engine for deciding how aggressively to exploit learned signals.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import pstdev

from backend.models.abc import UserStrategyProfile
from backend.models.career import UserProfile
from backend.models.intelligence import CareerDiscoveryResult, ConfidenceEstimate, ConversationalIntent
from backend.storage.records import BehaviorEventRecord, OutcomeRecord, RecommendationEventRecord, utc_now
from backend.storage.repository import HuntRepository


@dataclass(slots=True)
class ConfidenceService:
    """Estimates how reliable current recommendations are."""

    repository: HuntRepository

    async def estimate(
        self,
        *,
        user_id: str,
        profile: UserProfile | None,
        intent: ConversationalIntent,
        discovery: CareerDiscoveryResult,
        strategy_profile: UserStrategyProfile,
    ) -> ConfidenceEstimate:
        recommendations, behaviors, outcomes = await self.repository.list_abc_records(user_id)
        profile_completeness = self._profile_completeness(profile)
        behavioral_consistency = self._behavioral_consistency(strategy_profile, behaviors, intent)
        outcome_reliability = self._outcome_reliability(outcomes)
        data_volume_score = self._data_volume_score(recommendations, behaviors, outcomes)
        confidence = round(
            profile_completeness * 0.25
            + behavioral_consistency * 0.35
            + outcome_reliability * 0.25
            + data_volume_score * 0.15,
            4,
        )
        exploration_mode = bool(
            confidence < 0.55
            or (intent.exploration_mode and confidence < 0.70)
            or discovery.ambiguity_score >= 0.65
        )
        ranking_aggressiveness = round(0.25 + confidence * 0.65, 4)
        reasons = self._reasons(
            profile_completeness=profile_completeness,
            behavioral_consistency=behavioral_consistency,
            outcome_reliability=outcome_reliability,
            data_volume_score=data_volume_score,
        )
        recommended_role = (
            discovery.career_paths[0].role
            if discovery.career_paths
            else None
        )
        return ConfidenceEstimate(
            recommended_role=recommended_role,
            confidence=confidence,
            profile_completeness=profile_completeness,
            behavioral_consistency=behavioral_consistency,
            outcome_reliability=outcome_reliability,
            data_volume_score=data_volume_score,
            exploration_mode=exploration_mode,
            ranking_aggressiveness=ranking_aggressiveness,
            confidence_reason=reasons,
            updated_at=utc_now(),
        )

    @staticmethod
    def _profile_completeness(profile: UserProfile | None) -> float:
        if profile is None:
            return 0.0
        fields = [
            bool(profile.skills),
            bool(profile.education and profile.education.strip()),
            bool(profile.experience and profile.experience.strip()),
            bool(profile.interests),
        ]
        enrichment = [
            bool(profile.preferred_locations),
            bool(profile.github_topics),
            bool(profile.learning_history),
        ]
        return round(sum(fields) / len(fields) * 0.8 + sum(enrichment) / len(enrichment) * 0.2, 4)

    @staticmethod
    def _behavioral_consistency(
        strategy_profile: UserStrategyProfile,
        behaviors: list[BehaviorEventRecord],
        intent: ConversationalIntent,
    ) -> float:
        if not behaviors:
            return 0.1
        category_counts: dict[str, int] = {}
        for event in behaviors:
            category_counts[event.category] = category_counts.get(event.category, 0) + 1
        total = sum(category_counts.values()) or 1
        concentration = max(category_counts.values()) / total
        intent_top = max(intent.category_preferences.values()) if intent.category_preferences else 0.0
        profile_confidence = max(
            (stats.confidence for stats in strategy_profile.category_profiles.values()),
            default=0.0,
        )
        return round(
            min(
                1.0,
                concentration * 0.45 + intent_top * 0.25 + profile_confidence * 0.30,
            ),
            4,
        )

    @staticmethod
    def _outcome_reliability(outcomes: list[OutcomeRecord]) -> float:
        if not outcomes:
            return 0.0
        volume = min(1.0, len(outcomes) / 10)
        response_times = [outcome.response_time_days for outcome in outcomes if outcome.response_time_days > 0]
        if len(response_times) < 2:
            response_stability = 0.4
        else:
            variability = pstdev(response_times) / max(sum(response_times) / len(response_times), 1.0)
            response_stability = max(0.0, min(1.0, 1 - variability))
        return round(volume * 0.65 + response_stability * 0.35, 4)

    @staticmethod
    def _data_volume_score(
        recommendations: list[RecommendationEventRecord],
        behaviors: list[BehaviorEventRecord],
        outcomes: list[OutcomeRecord],
    ) -> float:
        session_count = len({record.session_id for record in recommendations})
        raw = min(1.0, session_count / 5) * 0.25
        raw += min(1.0, len(behaviors) / 15) * 0.35
        raw += min(1.0, len(outcomes) / 10) * 0.40
        return round(min(1.0, raw), 4)

    @staticmethod
    def _reasons(
        *,
        profile_completeness: float,
        behavioral_consistency: float,
        outcome_reliability: float,
        data_volume_score: float,
    ) -> list[str]:
        reasons: list[str] = []
        if profile_completeness >= 0.7:
            reasons.append("Profile information is reasonably complete")
        else:
            reasons.append("Profile information is still incomplete")
        if behavioral_consistency >= 0.6:
            reasons.append("Behavior is stable across repeated interactions")
        else:
            reasons.append("Behavior is still inconsistent or sparse")
        if outcome_reliability >= 0.6:
            reasons.append("Outcome evidence is sufficiently reliable")
        else:
            reasons.append("Outcome evidence is limited or unstable")
        if data_volume_score >= 0.6:
            reasons.append("There is enough repeated data to support personalization")
        else:
            reasons.append("The system is still learning from limited data volume")
        return reasons
