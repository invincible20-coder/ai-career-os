"""
Probabilistic long-term career compatibility modeling.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import fmean

from backend.models.abc import UserStrategyProfile
from backend.models.intelligence import UserIntelligenceState
from backend.models.resume_intelligence import (
    CareerPrediction,
    CareerVector,
    PredictiveCareerProfile,
    ResumeCorrelationProfile,
    UserCareerVector,
)
from backend.services.abc_service import ABCAdaptiveService
from backend.services.resume_correlation_service import ResumeCorrelationService
from backend.storage.records import BehaviorEventRecord, utc_now
from backend.storage.repository import HuntRepository


_CAREER_VECTORS = {
    "backend": (
        "Backend Engineering",
        CareerVector(
            technical_depth=0.95,
            system_design=0.92,
            analytical_reasoning=0.82,
            communication=0.45,
            creativity=0.45,
            leadership=0.42,
            exploration_tendency=0.35,
        ),
    ),
    "frontend": (
        "Frontend Engineering",
        CareerVector(
            technical_depth=0.78,
            system_design=0.60,
            analytical_reasoning=0.70,
            communication=0.58,
            creativity=0.78,
            leadership=0.40,
            exploration_tendency=0.52,
        ),
    ),
    "data": (
        "Data Analytics",
        CareerVector(
            technical_depth=0.76,
            system_design=0.55,
            analytical_reasoning=0.96,
            communication=0.56,
            creativity=0.48,
            leadership=0.38,
            exploration_tendency=0.44,
        ),
    ),
    "devops": (
        "Platform Engineering",
        CareerVector(
            technical_depth=0.90,
            system_design=0.90,
            analytical_reasoning=0.82,
            communication=0.46,
            creativity=0.42,
            leadership=0.48,
            exploration_tendency=0.38,
        ),
    ),
    "mobile": (
        "Mobile Engineering",
        CareerVector(
            technical_depth=0.80,
            system_design=0.68,
            analytical_reasoning=0.72,
            communication=0.48,
            creativity=0.72,
            leadership=0.36,
            exploration_tendency=0.50,
        ),
    ),
    "design": (
        "Product Design",
        CareerVector(
            technical_depth=0.34,
            system_design=0.30,
            analytical_reasoning=0.54,
            communication=0.82,
            creativity=0.96,
            leadership=0.46,
            exploration_tendency=0.72,
        ),
    ),
    "management": (
        "Technical Program Management",
        CareerVector(
            technical_depth=0.48,
            system_design=0.58,
            analytical_reasoning=0.68,
            communication=0.92,
            creativity=0.56,
            leadership=0.96,
            exploration_tendency=0.48,
        ),
    ),
    "non_technical": (
        "Business Operations",
        CareerVector(
            technical_depth=0.22,
            system_design=0.22,
            analytical_reasoning=0.58,
            communication=0.90,
            creativity=0.62,
            leadership=0.72,
            exploration_tendency=0.64,
        ),
    ),
}


@dataclass(slots=True)
class PredictiveCareerService:
    """Models evolving compatibility and trajectory under uncertainty."""

    repository: HuntRepository
    abc_service: ABCAdaptiveService
    resume_service: ResumeCorrelationService

    async def get_profile(
        self,
        *,
        user_id: str,
        intelligence_state: UserIntelligenceState,
    ) -> PredictiveCareerProfile:
        stored = await self.repository.get_predictive_career_profile(user_id)
        if stored is not None:
            return stored
        return await self.refresh_profile(
            user_id=user_id,
            intelligence_state=intelligence_state,
        )

    async def refresh_profile(
        self,
        *,
        user_id: str,
        intelligence_state: UserIntelligenceState,
    ) -> PredictiveCareerProfile:
        strategy_profile = await self.abc_service.get_strategy_profile(user_id)
        resume_profile = await self.resume_service.get_profile(user_id)
        _, behaviors, outcomes = await self.repository.list_abc_records(user_id)
        user_vector = await self._user_vector(
            user_id=user_id,
            intelligence_state=intelligence_state,
            resume_profile=resume_profile,
            behaviors=behaviors,
        )
        predictions = self._predictions(
            user_vector=user_vector,
            strategy_profile=strategy_profile,
            resume_profile=resume_profile,
            intelligence_state=intelligence_state,
            behavior_count=len(behaviors),
            outcome_count=len(outcomes),
        )
        profile = PredictiveCareerProfile(
            user_id=user_id,
            user_vector=user_vector,
            predictions=predictions,
            updated_at=utc_now(),
        )
        await self.repository.upsert_predictive_career_profile(profile)
        return profile

    async def _user_vector(
        self,
        *,
        user_id: str,
        intelligence_state: UserIntelligenceState,
        resume_profile: ResumeCorrelationProfile,
        behaviors: list[BehaviorEventRecord],
    ) -> UserCareerVector:
        fingerprints = await self.repository.list_resume_fingerprints(user_id)
        if fingerprints:
            technical_depth = fmean(
                fingerprint.features.technical_depth for fingerprint in fingerprints
            )
            communication = fmean(
                fingerprint.features.communication_indicators for fingerprint in fingerprints
            )
            analytical_reasoning = fmean(
                (
                    fingerprint.features.data_keywords / 10
                    + fingerprint.features.project_complexity_score
                )
                / 2
                for fingerprint in fingerprints
            )
            system_design = fmean(
                (
                    fingerprint.features.backend_keywords / 10
                    + fingerprint.features.project_complexity_score
                )
                / 2
                for fingerprint in fingerprints
            )
            creativity = fmean(
                (
                    fingerprint.features.frontend_keywords / 10
                    + fingerprint.features.skill_diversity
                )
                / 2
                for fingerprint in fingerprints
            )
            leadership = fmean(
                (
                    fingerprint.features.communication_indicators
                    + fingerprint.features.experience_depth
                )
                / 2
                for fingerprint in fingerprints
            )
            resume_evidence = min(1.0, len(fingerprints) / 5)
        else:
            technical_depth = 0.35
            communication = 0.35
            analytical_reasoning = 0.35
            system_design = 0.35
            creativity = 0.35
            leadership = 0.25
            resume_evidence = 0.0

        category_concentration = self._behavior_concentration(behaviors)
        intent = intelligence_state.intent
        commitment = intent.commitment_level
        exploration = max(intent.curiosity, intent.uncertainty)
        learned_signal = max(
            (estimate.effectiveness_score for estimate in resume_profile.resume_effectiveness.values()),
            default=0.35,
        )
        blend = 0.65 + resume_evidence * 0.20
        return UserCareerVector(
            technical_depth=self._clamp(technical_depth * blend + learned_signal * 0.15),
            system_design=self._clamp(system_design * blend + category_concentration * 0.15),
            analytical_reasoning=self._clamp(
                analytical_reasoning * blend + learned_signal * 0.10
            ),
            communication=self._clamp(communication * 0.75 + commitment * 0.25),
            creativity=self._clamp(creativity * 0.70 + exploration * 0.30),
            leadership=self._clamp(leadership * 0.75 + commitment * 0.25),
            exploration_tendency=self._clamp(exploration),
        )

    def _predictions(
        self,
        *,
        user_vector: UserCareerVector,
        strategy_profile: UserStrategyProfile,
        resume_profile: ResumeCorrelationProfile,
        intelligence_state: UserIntelligenceState,
        behavior_count: int,
        outcome_count: int,
    ) -> list[CareerPrediction]:
        behavior_consistency = intelligence_state.confidence.behavioral_consistency
        intent = intelligence_state.intent
        top_resume_effectiveness = max(
            (estimate.effectiveness_score for estimate in resume_profile.resume_effectiveness.values()),
            default=0.35,
        )
        evidence_volume = min(1.0, behavior_count / 15) * 0.45 + min(1.0, outcome_count / 10) * 0.55
        predictions: list[CareerPrediction] = []
        for category, (role, career_vector) in _CAREER_VECTORS.items():
            compatibility = self._cosine_similarity(user_vector, career_vector)
            category_profile = strategy_profile.category_profiles.get(category)
            learned_weight = strategy_profile.category_weights.get(category, 0.5)
            outcome_signal = category_profile.success_rate if category_profile else 0.25
            growth_potential = self._clamp(
                compatibility * 0.45
                + top_resume_effectiveness * 0.20
                + outcome_signal * 0.20
                + learned_weight * 0.15
            )
            trajectory_stability = self._clamp(
                behavior_consistency * 0.45
                + intent.career_clarity * 0.35
                + (1 - intent.uncertainty) * 0.20
            )
            persistence_probability = self._clamp(
                compatibility * 0.40
                + intent.commitment_level * 0.25
                + behavior_consistency * 0.20
                + learned_weight * 0.15
            )
            adaptability = self._clamp(
                user_vector.exploration_tendency * 0.45
                + user_vector.creativity * 0.25
                + user_vector.communication * 0.15
                + user_vector.analytical_reasoning * 0.15
            )
            confidence = self._clamp(
                intelligence_state.confidence.confidence * 0.45
                + evidence_volume * 0.35
                + (
                    max(
                        (
                            estimate.confidence
                            for estimate in resume_profile.resume_effectiveness.values()
                        ),
                        default=0.0,
                    )
                )
                * 0.20
            )
            predictions.append(
                CareerPrediction(
                    role=role,
                    category=category,
                    compatibility=round(compatibility, 4),
                    growth_potential=round(growth_potential, 4),
                    trajectory_stability=round(trajectory_stability, 4),
                    persistence_probability=round(persistence_probability, 4),
                    adaptability=round(adaptability, 4),
                    confidence=round(confidence, 4),
                    uncertainty=round(1 - confidence, 4),
                    reason=self._reason(
                        category=category,
                        compatibility=compatibility,
                        confidence=confidence,
                        trajectory_stability=trajectory_stability,
                    ),
                )
            )
        return sorted(predictions, key=lambda prediction: prediction.compatibility, reverse=True)

    @staticmethod
    def _behavior_concentration(behaviors: list[BehaviorEventRecord]) -> float:
        if not behaviors:
            return 0.0
        counts: dict[str, int] = {}
        for behavior in behaviors:
            counts[behavior.category] = counts.get(behavior.category, 0) + 1
        return max(counts.values()) / len(behaviors)

    @staticmethod
    def _cosine_similarity(left: CareerVector, right: CareerVector) -> float:
        left_values = list(left.model_dump().values())
        right_values = list(right.model_dump().values())
        numerator = sum(a * b for a, b in zip(left_values, right_values, strict=False))
        left_norm = math.sqrt(sum(value * value for value in left_values))
        right_norm = math.sqrt(sum(value * value for value in right_values))
        if math.isclose(left_norm, 0.0) or math.isclose(right_norm, 0.0):
            return 0.0
        return PredictiveCareerService._clamp(numerator / (left_norm * right_norm))

    @staticmethod
    def _reason(
        *,
        category: str,
        compatibility: float,
        confidence: float,
        trajectory_stability: float,
    ) -> str:
        if confidence < 0.4:
            return "Insufficient long-term behavioral evidence; prediction remains highly uncertain"
        if trajectory_stability < 0.45:
            return f"{category} is plausible, but the current trajectory is still unstable"
        if compatibility >= 0.75:
            return f"{category} shows strong multi-signal compatibility"
        return f"{category} remains a moderate-fit probabilistic path"

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))
