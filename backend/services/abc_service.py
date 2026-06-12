"""
ABC-driven adaptive job recommendation and re-ranking service.
"""

from __future__ import annotations

import re
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from math import pow
from time import perf_counter
from typing import Any

from backend.core.logger import get_logger
from backend.models.abc import (
    BehaviorEvent,
    BehaviorEventCreate,
    BehaviorEventType,
    CategoryStrategyStats,
    OutcomeCreate,
    OutcomeEvent,
    OutcomeType,
    RankedJob,
    RecommendationEvent,
    UserStrategyProfile,
)
from backend.models.abc_intelligence import (
    ConsequenceLevel,
    consequence_weight_for,
)
from backend.models.career import UserProfile
from backend.models.errors import ErrorDetail
from backend.models.job import Job
from backend.services.career_discovery_service import CareerDiscoveryService
from backend.services.confidence_service import ConfidenceService
from backend.services.event_bus import EventBus
from backend.services.exceptions import BadRequestError
from backend.storage.records import (
    BehaviorEventRecord,
    OutcomeRecord,
    RecommendationEventRecord,
    utc_now,
)
from backend.storage.repository import HuntRepository


_CATEGORIES = (
    "backend",
    "frontend",
    "data",
    "devops",
    "mobile",
    "design",
    "management",
    "non_technical",
    "general",
)
_NEUTRAL_WEIGHT = 0.5
_DECAY_HALF_LIFE_DAYS = 30.0
logger = get_logger(__name__)


@dataclass(slots=True)
class ABCAdaptiveService:
    """Closed-loop A -> B -> C -> strategy update -> re-ranking engine.

    V2.0 enhancements: immutable event store, dual memory, semantic similarity,
    pattern discovery, consequence weighting, exploration/exploitation,
    career persona alignment, and enhanced explainability.
    """

    repository: HuntRepository
    confidence_service: ConfidenceService | None = None
    discovery_service: CareerDiscoveryService | None = None
    event_bus: EventBus | None = None
    # V2 optional service dependencies (injected when available)
    memory_service: object | None = None
    pattern_service: object | None = None
    semantic_service: object | None = None
    persona_service: object | None = None

    async def rank_jobs(
        self,
        *,
        user_id: str,
        hunt_id: str,
        session_id: str,
        goal: str,
        jobs: list[Job],
        profile: UserProfile | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[RankedJob]:
        if not jobs:
            return []

        filters = filters or {}
        started_at = perf_counter()
        strategy_profile = await self.get_strategy_profile(user_id)
        category_weights = self._normalised_weights(strategy_profile.category_weights)
        intent = None
        discovery = None
        confidence = None
        if self.discovery_service is not None and self.confidence_service is not None:
            from backend.services.intent_service import ConversationalIntentService

            intent = await ConversationalIntentService(self.repository).get_intent(user_id)
            discovery = self.discovery_service.discover(
                intent=intent,
                strategy_profile=strategy_profile,
                profile=profile,
            )
            confidence = await self.confidence_service.estimate(
                user_id=user_id,
                profile=profile,
                intent=intent,
                discovery=discovery,
                strategy_profile=strategy_profile,
            )
        history = await self.repository.recent_recommendation_history(
            user_id,
            [job.job_id for job in jobs],
        )

        scored: list[RankedJob] = []
        for job in jobs:
            category = self.classify_job(job)
            category_profile = strategy_profile.category_profiles.get(category)
            keyword_match = self.keyword_match(job, goal)
            skill_match = self.skill_match(job, profile)
            education_match = self.education_match(job, profile)
            experience_match = self.experience_match(job, profile)
            location_match = self.location_match(job, profile)
            base_score = self.base_match_score(
                keyword_match=keyword_match,
                skill_match=skill_match,
                education_match=education_match,
                experience_match=experience_match,
                location_match=location_match,
            )
            behavior_score = self._behavior_score(category_profile)
            outcome_score = self._outcome_score(category_profile)
            category_weight = self._category_weight(category_profile, category_weights[category])
            evidence_strength = self._evidence_strength(category_profile)
            confidence_score = (
                confidence.confidence
                if confidence is not None
                else evidence_strength
            )
            aggressiveness = confidence.ranking_aggressiveness if confidence is not None else 0.25
            exploration_bonus = self._exploration_bonus(
                category,
                discovery,
                confidence_score,
            )
            trust_score = job.trust_score if job.trust_score is not None else 1.0
            trust_penalty = round((1 - trust_score) * 0.10 + min(0.10, len(job.scam_flags) * 0.03), 4)
            previous_score, exposure_count = history.get(job.job_id, (base_score, 0))
            repetition_penalty = self._repetition_penalty(exposure_count)

            # V2: Compute additional intelligence signals
            semantic_score = 0.0
            pattern_score = 0.0
            temporal_score = base_score
            memory_score = 0.0
            persona_alignment_val = 0.5
            v2_signal_count = 0  # Require ≥2 V2 signals before switching formula
            job_signature = self._build_job_signature(job)

            if self.semantic_service is not None:
                try:
                    successful_sigs = []
                    if self.pattern_service is not None:
                        top_patterns = await self.pattern_service.get_top_patterns(
                            user_id, min_confidence=0.3, limit=10,
                        )
                        successful_sigs = [p.antecedent_signature for p in top_patterns]
                    if successful_sigs:
                        semantic_score = self.semantic_service.semantic_score_for_job(
                            job_signature, successful_sigs,
                        )
                        v2_signal_count += 1
                except Exception:
                    pass

            if self.pattern_service is not None:
                try:
                    top_patterns = await self.pattern_service.get_top_patterns(
                        user_id, min_confidence=0.2, limit=15,
                    )
                    if top_patterns:
                        pattern_score = self.pattern_service.pattern_score_for_job(
                            top_patterns, category, job_signature,
                        )
                        v2_signal_count += 1
                except Exception:
                    pass

            if self.memory_service is not None:
                try:
                    memory_state = await self.memory_service.get_memory_state(user_id)
                    has_memory = bool(
                        memory_state.short_term.recent_interests
                        or memory_state.short_term.recent_applications
                        or memory_state.long_term.stable_preferences
                        or memory_state.long_term.successful_patterns
                    )
                    if has_memory:
                        job_keywords = self._terms(
                            " ".join([job.title, job.description, " ".join(job.requirements)])
                        )
                        memory_score = self.memory_service.memory_influenced_score(
                            memory_state, category, job_keywords,
                        )
                        v2_signal_count += 1
                except Exception:
                    pass

            if self.persona_service is not None:
                try:
                    persona = await self.persona_service.get_persona(user_id)
                    if persona.persona_confidence > 0.1:
                        persona_alignment_val = self.persona_service.persona_alignment_score(
                            persona, category,
                        )
                        v2_signal_count += 1
                except Exception:
                    pass

            # Ranking formula: V2 progressively blends in as data accumulates.
            # When V2 has insufficient data (<2 signal sources), falls back to V1 formula.
            if v2_signal_count >= 2:
                v2_behavioral = behavior_score * 0.5 + memory_score * 0.3 + persona_alignment_val * 0.2
                exploration_score_val = self._exploration_bonus(category, discovery, confidence_score)
                learned_score = (
                    v2_behavioral * 0.30
                    + semantic_score * 0.20
                    + outcome_score * 0.20
                    + base_score * 0.15
                    + confidence_score * 0.10
                    + exploration_score_val * 0.05
                )
            else:
                # V1 formula (backward compatible)
                learned_score = (
                    base_score * 0.35
                    + behavior_score * 0.25
                    + outcome_score * 0.25
                    + category_weight * 0.15
                )
            confidence_blended_score = base_score * (1 - aggressiveness) + learned_score * aggressiveness
            # Use V2 exploration when we have data, else V1
            if v2_signal_count >= 2:
                exploration_bonus = self._v2_exploration_bonus(
                    category, discovery, confidence_score, pattern_score,
                )
            else:
                exploration_bonus = self._exploration_bonus(
                    category, discovery, confidence_score,
                )
            raw_score = max(
                0.0,
                min(1.0, confidence_blended_score + exploration_bonus - repetition_penalty),
            )
            final_score = round(
                previous_score * 0.35 + raw_score * 0.65
                if exposure_count
                else raw_score,
                4,
            )
            final_score = round(max(0.0, final_score - trust_penalty), 4)
            scored.append(
                RankedJob(
                    job=job,
                    event_id=str(uuid.uuid4()),
                    job_id=job.job_id,
                    rank=0,
                    job_category=category,
                    keyword_match=keyword_match,
                    skill_match=skill_match,
                    education_match=education_match,
                    experience_match=experience_match,
                    location_match=location_match,
                    base_match_score=base_score,
                    behavior_score=behavior_score,
                    outcome_score=outcome_score,
                    category_weight=category_weight,
                    confidence=confidence_score,
                    confidence_percent=round(confidence_score * 100, 2),
                    uncertainty_percent=round((1 - confidence_score) * 100, 2),
                    evidence_strength=evidence_strength,
                    exploration_bonus=exploration_bonus,
                    repetition_penalty=repetition_penalty,
                    final_score=final_score,
                    reason=self._reason(
                        category,
                        base_score,
                        category_profile,
                        confidence,
                        discovery,
                    ),
                    explanation=self._explanation(
                        category=category,
                        base_score=base_score,
                        behavior_score=behavior_score,
                        outcome_score=outcome_score,
                        category_weight=category_weight,
                        confidence_score=confidence_score,
                        profile=category_profile,
                    ),
                    signal_breakdown={
                        "base_match_score": base_score,
                        "behavior_score": behavior_score,
                        "outcome_score": outcome_score,
                        "category_weight": category_weight,
                        "exploration_bonus": exploration_bonus,
                        "repetition_penalty": repetition_penalty,
                        "trust_penalty": trust_penalty,
                        "semantic_score": semantic_score,
                        "pattern_score": pattern_score,
                        "memory_score": memory_score,
                        "persona_alignment": persona_alignment_val,
                    },
                    strategy_weights=category_weights,
                    filters=filters,
                    semantic_score=semantic_score,
                    pattern_score=pattern_score,
                    temporal_score=base_score,
                    memory_score=memory_score,
                    persona_alignment=persona_alignment_val,
                )
            )

        scored.sort(
            key=lambda item: (
                item.final_score,
                item.base_match_score,
                item.job.company.lower(),
            ),
            reverse=True,
        )

        events: list[RecommendationEvent] = []
        ranked: list[RankedJob] = []
        now = utc_now()
        for index, ranked_job in enumerate(scored, start=1):
            job = ranked_job.job.model_copy(
                update={
                    "ranking_position": index,
                    "base_match_score": ranked_job.base_match_score,
                    "final_score": ranked_job.final_score,
                    "recommendation_reason": ranked_job.reason,
                    "recommendation_event_id": ranked_job.event_id,
                    "job_category": ranked_job.job_category,
                }
            )
            updated = ranked_job.model_copy(update={"rank": index, "job": job})
            ranked.append(updated)
            events.append(
                RecommendationEvent(
                    event_id=updated.event_id,
                    user_id=user_id,
                    hunt_id=hunt_id,
                    job_id=updated.job_id,
                    ranking_position=index,
                    base_match_score=updated.base_match_score,
                    final_score=updated.final_score,
                    recommendation_reason=updated.reason,
                    strategy_weights_used=updated.strategy_weights,
                    filters_applied={
                        **updated.filters,
                        "signal_breakdown": updated.signal_breakdown,
                        "explanation": updated.explanation,
                        "confidence": updated.confidence,
                        "uncertainty_percent": updated.uncertainty_percent,
                    },
                    session_id=session_id,
                    job_category=updated.job_category,
                    timestamp=now,
                )
            )

        await self.repository.save_recommendation_events(events)
        await self._publish(
            session_id,
            {
                "type": "recommendations_ranked",
                "user_id": user_id,
                "hunt_id": hunt_id,
                "recommendations": [
                    {
                        "job_id": item.job_id,
                        "rank": item.rank,
                        "category": item.job_category,
                        "final_score": item.final_score,
                        "reason": item.reason,
                    }
                    for item in ranked
                ],
            },
        )
        logger.info(
            "abc_recommendations_ranked",
            extra={
                "event": "abc_recommendations_ranked",
                "user_id": user_id,
                "hunt_id": hunt_id,
                "session_id": session_id,
                "jobs_ranked": len(ranked),
                "top_job_id": ranked[0].job_id if ranked else None,
                "top_category": ranked[0].job_category if ranked else None,
                "top_score": ranked[0].final_score if ranked else None,
                "latency_ms": int((perf_counter() - started_at) * 1000),
            },
        )
        return ranked

    async def log_behavior(self, payload: BehaviorEventCreate) -> BehaviorEvent:
        antecedent = await self.repository.get_recommendation_event_record(
            payload.antecedent_event_id
        )
        self._validate_behavior_context(payload, antecedent)

        event = BehaviorEvent(
            event_id=str(uuid.uuid4()),
            antecedent_event_id=antecedent.id,
            user_id=payload.user_id or antecedent.user_id,
            hunt_id=payload.hunt_id or antecedent.hunt_id,
            session_id=payload.session_id or antecedent.session_id,
            event_type=payload.event_type,
            job_id=payload.job_id or antecedent.job_id,
            resume_id=payload.resume_id,
            job_category=payload.job_category or antecedent.category,
            timestamp=utc_now(),
        )
        await self.repository.save_behavior_event(event)
        await self.refresh_strategy_profile(event.user_id)
        await self._publish(
            event.session_id,
            {
                "type": "behavior_logged",
                "user_id": event.user_id,
                "hunt_id": event.hunt_id,
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "job_id": event.job_id,
                "category": event.job_category,
            },
        )
        logger.info(
            "abc_behavior_logged",
            extra={
                "event": "abc_behavior_logged",
                "user_id": event.user_id,
                "hunt_id": event.hunt_id,
                "session_id": event.session_id,
                "behavior_event_id": event.event_id,
                "antecedent_event_id": event.antecedent_event_id,
                "event_type": event.event_type.value,
                "job_id": event.job_id,
                "category": event.job_category,
            },
        )
        return event

    async def log_outcome(self, payload: OutcomeCreate) -> OutcomeEvent:
        behavior = await self.repository.get_behavior_event_record(payload.behavior_event_id)
        event = OutcomeEvent(
            outcome_id=str(uuid.uuid4()),
            behavior_event_id=behavior.id,
            outcome_type=payload.outcome_type,
            response_time_days=payload.response_time_days,
            timestamp=utc_now(),
        )
        await self.repository.save_outcome_event(event)
        await self.refresh_strategy_profile(behavior.user_id)

        # V2: Write to immutable learning event store
        await self._write_learning_event(
            behavior=behavior,
            outcome_event=event,
        )

        # V2: Update dual memory with outcome signal
        if self.memory_service is not None:
            try:
                consequence_level = self._map_outcome_to_consequence(event.outcome_type.value)
                if consequence_level in (
                    ConsequenceLevel.INTERVIEW.value,
                    ConsequenceLevel.OFFER.value,
                    ConsequenceLevel.ACCEPTED.value,
                ):
                    await self.memory_service.update_long_term(
                        behavior.user_id,
                        successful_pattern=behavior.category,
                        category=behavior.category,
                    )
            except Exception:
                pass

        # V2: Evolve persona after new outcome
        if self.persona_service is not None:
            try:
                await self.persona_service.evolve_persona(behavior.user_id)
            except Exception:
                pass

        await self._publish(
            behavior.session_id,
            {
                "type": "outcome_logged",
                "user_id": behavior.user_id,
                "hunt_id": behavior.hunt_id,
                "outcome_id": event.outcome_id,
                "outcome_type": event.outcome_type.value,
                "job_id": behavior.job_id,
                "category": behavior.category,
            },
        )
        logger.info(
            "abc_outcome_logged",
            extra={
                "event": "abc_outcome_logged",
                "user_id": behavior.user_id,
                "hunt_id": behavior.hunt_id,
                "session_id": behavior.session_id,
                "outcome_id": event.outcome_id,
                "behavior_event_id": event.behavior_event_id,
                "outcome_type": event.outcome_type.value,
                "response_time_days": event.response_time_days,
                "job_id": behavior.job_id,
                "category": behavior.category,
            },
        )
        return event

    async def get_strategy_profile(self, user_id: str) -> UserStrategyProfile:
        profile = await self.repository.get_user_strategy_profile(user_id)
        if profile is not None:
            return profile
        return self._empty_profile(user_id)

    async def refresh_strategy_profile(self, user_id: str) -> UserStrategyProfile:
        old_profile = await self.get_strategy_profile(user_id)
        recommendation_records, behavior_records, outcome_records = await self.repository.list_abc_records(
            user_id
        )
        profile = self._compute_profile(
            user_id=user_id,
            old_profile=old_profile,
            recommendation_records=recommendation_records,
            behavior_records=behavior_records,
            outcome_records=outcome_records,
        )
        await self.repository.upsert_user_strategy_profile(profile)
        logger.info(
            "abc_strategy_profile_refreshed",
            extra={
                "event": "abc_strategy_profile_refreshed",
                "user_id": user_id,
                "category_weights": profile.category_weights,
                "updated_at": profile.updated_at.isoformat(),
            },
        )
        return profile

    def _compute_profile(
        self,
        *,
        user_id: str,
        old_profile: UserStrategyProfile,
        recommendation_records: list[RecommendationEventRecord],
        behavior_records: list[BehaviorEventRecord],
        outcome_records: list[OutcomeRecord],
    ) -> UserStrategyProfile:
        now = utc_now()
        shown_by_category: dict[str, float] = defaultdict(float)
        clicks_by_category: dict[str, float] = defaultdict(float)
        starts_by_category: dict[str, float] = defaultdict(float)
        applications_by_category: dict[str, float] = defaultdict(float)
        abandons_by_category: dict[str, float] = defaultdict(float)
        ignores_by_category: dict[str, float] = defaultdict(float)
        resume_selected_by_category: dict[str, float] = defaultdict(float)
        behaviors_by_category: dict[str, float] = defaultdict(float)
        outcomes_by_category: dict[str, float] = defaultdict(float)
        success_by_category: dict[str, float] = defaultdict(float)
        interviews_by_category: dict[str, float] = defaultdict(float)
        offers_by_category: dict[str, float] = defaultdict(float)
        followups_by_category: dict[str, float] = defaultdict(float)
        rejections_by_category: dict[str, float] = defaultdict(float)
        no_response_by_category: dict[str, float] = defaultdict(float)
        response_time_by_category: dict[str, float] = defaultdict(float)
        response_weight_by_category: dict[str, float] = defaultdict(float)

        behavior_by_id = {record.id: record for record in behavior_records}

        for record in recommendation_records:
            shown_by_category[record.category] += self._decay(record.created_at, now)

        for record in behavior_records:
            weight = self._decay(record.created_at, now)
            category = record.category
            behaviors_by_category[category] += weight
            if record.event_type in {
                BehaviorEventType.JOB_VIEWED.value,
                BehaviorEventType.JOB_CLICKED.value,
            }:
                clicks_by_category[category] += weight
            if record.event_type == BehaviorEventType.APPLICATION_STARTED.value:
                starts_by_category[category] += weight
            if record.event_type == BehaviorEventType.APPLICATION_COMPLETED.value:
                applications_by_category[category] += weight
            if record.event_type == BehaviorEventType.APPLICATION_ABANDONED.value:
                abandons_by_category[category] += weight
            if record.event_type == BehaviorEventType.JOB_IGNORED.value:
                ignores_by_category[category] += weight
            if record.event_type == BehaviorEventType.RESUME_SELECTED.value and record.resume_id:
                resume_selected_by_category[category] += weight

        for record in outcome_records:
            behavior = behavior_by_id.get(record.behavior_event_id)
            if behavior is None:
                continue
            weight = self._decay(record.created_at, now)
            category = behavior.category
            outcomes_by_category[category] += weight
            if record.outcome_type == OutcomeType.INTERVIEW.value:
                interviews_by_category[category] += weight
                success_by_category[category] += weight
                response_time_by_category[category] += max(record.response_time_days, 0.1) * weight
                response_weight_by_category[category] += weight
            elif record.outcome_type == OutcomeType.OFFER.value:
                offers_by_category[category] += weight
                success_by_category[category] += weight
                response_time_by_category[category] += max(record.response_time_days, 0.1) * weight
                response_weight_by_category[category] += weight
            elif record.outcome_type == OutcomeType.FOLLOW_UP_REQUESTED.value:
                followups_by_category[category] += weight
                success_by_category[category] += weight * 0.6
                response_time_by_category[category] += max(record.response_time_days, 0.1) * weight
                response_weight_by_category[category] += weight
            elif record.outcome_type == OutcomeType.REJECTION.value:
                rejections_by_category[category] += weight
            elif record.outcome_type == OutcomeType.NO_RESPONSE.value:
                no_response_by_category[category] += weight

        category_profiles: dict[str, CategoryStrategyStats] = {}
        weights: dict[str, float] = {}
        success_rates: dict[str, float] = {}
        click_rates: dict[str, float] = {}
        application_rates: dict[str, float] = {}
        avg_response_times: dict[str, float] = {}

        for category in _CATEGORIES:
            shown = shown_by_category[category]
            clicks = clicks_by_category[category]
            starts = starts_by_category[category]
            applications = applications_by_category[category]
            abandons = abandons_by_category[category]
            ignores = ignores_by_category[category]
            outcomes = outcomes_by_category[category]
            successes = success_by_category[category]
            no_responses = no_response_by_category[category]
            avg_response = (
                response_time_by_category[category] / response_weight_by_category[category]
                if response_weight_by_category[category]
                else 7.0
            )
            click_rate = self._smoothed_rate(clicks, max(shown, clicks), prior=0.35)
            application_rate = self._smoothed_rate(
                applications,
                max(shown, applications),
                prior=0.25,
            )
            abandonment_rate = self._smoothed_rate(abandons, max(starts, applications), prior=0.15)
            ignore_rate = self._smoothed_rate(ignores, max(shown, ignores), prior=0.1)
            success_rate = self._smoothed_rate(successes, max(applications, outcomes), prior=0.25)
            response_speed = min(1.0, 1 / max(avg_response, 1.0))
            resume_effectiveness = self._smoothed_rate(
                successes,
                max(resume_selected_by_category[category], applications),
                prior=0.25,
            )
            score = round(
                success_rate * 0.40
                + click_rate * 0.20
                + application_rate * 0.15
                + response_speed * 0.15
                + resume_effectiveness * 0.10,
                4,
            )
            score = round(max(0.0, score - ignore_rate * 0.10), 4)
            previous_weight = old_profile.category_weights.get(category, _NEUTRAL_WEIGHT)
            raw_weight = previous_weight * 0.7 + score * 0.3
            confidence = min(1.0, (shown + behaviors_by_category[category] * 0.05 + outcomes) / 8.0)
            weight = round(_NEUTRAL_WEIGHT * (1 - confidence) + raw_weight * confidence, 4)

            stats = CategoryStrategyStats(
                applications_count=round(applications),
                interviews_count=round(interviews_by_category[category]),
                rejection_count=round(rejections_by_category[category]),
                no_response_count=round(no_responses),
                offers_count=round(offers_by_category[category]),
                follow_up_count=round(followups_by_category[category]),
                success_rate=round(success_rate, 4),
                avg_response_time=round(avg_response, 4),
                click_rate=round(click_rate, 4),
                application_rate=round(application_rate, 4),
                abandonment_rate=round(abandonment_rate, 4),
                ignore_rate=round(ignore_rate, 4),
                resume_performance_score=round(resume_effectiveness, 4),
                recent_trend_score=score,
                score=score,
                weight=weight,
                confidence=round(confidence, 4),
            )
            category_profiles[category] = stats
            weights[category] = weight
            success_rates[category] = stats.success_rate
            click_rates[category] = stats.click_rate
            application_rates[category] = stats.application_rate
            avg_response_times[category] = stats.avg_response_time

        return UserStrategyProfile(
            user_id=user_id,
            category_weights=weights,
            category_success_rates=success_rates,
            click_rates=click_rates,
            application_rates=application_rates,
            avg_response_times=avg_response_times,
            category_profiles=category_profiles,
            updated_at=now,
        )

    @staticmethod
    def classify_job(job: Job) -> str:
        text = " ".join(
            [
                job.title,
                job.description,
                " ".join(job.requirements),
            ]
        ).lower()
        category_keywords = {
            "backend": {"backend", "api", "fastapi", "django", "flask", "database", "postgres", "redis"},
            "frontend": {"frontend", "react", "javascript", "typescript", "ui", "css", "web"},
            "data": {"data", "ml", "machine", "analytics", "etl", "pipeline", "pandas"},
            "devops": {"devops", "cloud", "docker", "kubernetes", "terraform", "sre", "infrastructure"},
            "mobile": {"mobile", "android", "ios", "swift", "kotlin", "react native"},
            "design": {"design", "ux", "figma", "visual", "prototype"},
            "management": {"management", "manager", "lead", "program", "operations"},
            "non_technical": {"sales", "marketing", "support", "business", "recruiting"},
        }
        scores = {
            category: sum(1 for keyword in keywords if keyword in text)
            for category, keywords in category_keywords.items()
        }
        best_category, best_score = max(scores.items(), key=lambda item: item[1])
        return best_category if best_score > 0 else "general"

    @staticmethod
    def keyword_match(job: Job, goal: str) -> float:
        goal_terms = ABCAdaptiveService._terms(goal)
        job_terms = ABCAdaptiveService._terms(
            " ".join([job.title, job.description, " ".join(job.requirements), job.location])
        )
        if not goal_terms:
            return 0.5
        overlap = len(goal_terms & job_terms)
        title_bonus = 0.15 if goal.lower() in job.title.lower() else 0.0
        return round(min(1.0, overlap / len(goal_terms) + title_bonus), 4)

    @staticmethod
    def skill_match(job: Job, profile: UserProfile | None) -> float:
        if profile is None or not profile.skills:
            return 0.5
        profile_terms = ABCAdaptiveService._terms(" ".join(profile.skills))
        job_terms = ABCAdaptiveService._terms(
            " ".join([job.title, job.description, " ".join(job.requirements)])
        )
        return ABCAdaptiveService._overlap_score(profile_terms, job_terms)

    @staticmethod
    def education_match(job: Job, profile: UserProfile | None) -> float:
        if profile is None or not profile.education:
            return 0.5
        return ABCAdaptiveService._overlap_score(
            ABCAdaptiveService._terms(profile.education),
            ABCAdaptiveService._terms(" ".join([job.description, " ".join(job.requirements)])),
        )

    @staticmethod
    def experience_match(job: Job, profile: UserProfile | None) -> float:
        if profile is None or not profile.experience:
            return 0.5
        return ABCAdaptiveService._overlap_score(
            ABCAdaptiveService._terms(profile.experience),
            ABCAdaptiveService._terms(" ".join([job.description, " ".join(job.requirements)])),
        )

    @staticmethod
    def location_match(job: Job, profile: UserProfile | None) -> float:
        if profile is None or not profile.preferred_locations:
            return 0.5
        job_location = job.location.lower()
        if any(location.lower() in job_location for location in profile.preferred_locations):
            return 1.0
        if "remote" in job_location:
            return 0.75
        return 0.0

    @staticmethod
    def base_match_score(
        *,
        keyword_match: float,
        skill_match: float,
        education_match: float,
        experience_match: float,
        location_match: float,
    ) -> float:
        core_score = (
            keyword_match * 0.30
            + skill_match * 0.30
            + experience_match * 0.20
            + location_match * 0.20
        )
        return round(core_score * 0.90 + education_match * 0.10, 4)

    @staticmethod
    def _terms(value: str) -> set[str]:
        stop_words = {"and", "the", "for", "with", "role", "job", "senior", "engineer"}
        return {
            token
            for token in re.findall(r"[a-z0-9]+", value.lower())
            if token not in stop_words and len(token) > 1
        }

    @staticmethod
    def _overlap_score(left: set[str], right: set[str]) -> float:
        if not left:
            return 0.5
        return round(min(1.0, len(left & right) / len(left)), 4)

    @staticmethod
    def _validate_behavior_context(
        payload: BehaviorEventCreate,
        antecedent: RecommendationEventRecord,
    ) -> None:
        mismatches = {}
        for field_name, expected in {
            "user_id": antecedent.user_id,
            "hunt_id": antecedent.hunt_id,
            "session_id": antecedent.session_id,
            "job_id": antecedent.job_id,
            "job_category": antecedent.category,
        }.items():
            provided = getattr(payload, field_name)
            if provided is not None and provided != expected:
                mismatches[field_name] = {"provided": provided, "expected": expected}
        if mismatches:
            raise BadRequestError(
                "Behavior event does not match its recommendation context",
                errors=[
                    ErrorDetail(
                        code="behavior_context_mismatch",
                        message="Behavior must reference the same user, job, hunt, and session as the antecedent",
                        details={"mismatches": mismatches},
                    )
                ],
            )

    @staticmethod
    def _normalised_weights(weights: dict[str, float]) -> dict[str, float]:
        return {category: round(weights.get(category, _NEUTRAL_WEIGHT), 4) for category in _CATEGORIES}

    @staticmethod
    def _category_weight(
        profile: CategoryStrategyStats | None,
        learned_weight: float,
    ) -> float:
        if profile is None:
            return _NEUTRAL_WEIGHT
        return round(_NEUTRAL_WEIGHT * (1 - profile.confidence) + learned_weight * profile.confidence, 4)

    @staticmethod
    def _behavior_score(profile: CategoryStrategyStats | None) -> float:
        if profile is None:
            return _NEUTRAL_WEIGHT
        session_engagement = min(
            1.0,
            profile.click_rate * 0.5 + profile.application_rate * 0.5,
        )
        base_behavior = (
            profile.click_rate * 0.40
            + profile.application_rate * 0.40
            - profile.abandonment_rate * 0.20
        )
        return round(
            max(
                0.0,
                min(
                    1.0,
                    base_behavior * 0.85
                    + session_engagement * 0.15
                    - profile.ignore_rate * 0.15,
                ),
            ),
            4,
        )

    @staticmethod
    def _outcome_score(profile: CategoryStrategyStats | None) -> float:
        if profile is None:
            return _NEUTRAL_WEIGHT
        rejection_rate = ABCAdaptiveService._smoothed_rate(
            profile.rejection_count + profile.no_response_count,
            max(
                profile.applications_count,
                profile.rejection_count + profile.no_response_count,
            ),
            prior=0.2,
        )
        response_speed = min(1.0, 1 / max(profile.avg_response_time, 1.0))
        offer_rate = ABCAdaptiveService._smoothed_rate(
            profile.offers_count,
            max(profile.applications_count, profile.offers_count),
            prior=0.05,
        )
        interview_rate = ABCAdaptiveService._smoothed_rate(
            profile.interviews_count,
            max(profile.applications_count, profile.interviews_count),
            prior=0.15,
        )
        core_outcome = (
            interview_rate * 0.50
            + offer_rate * 0.30
            + response_speed * 0.20
        )
        return round(
            core_outcome * 0.75 + (1 - rejection_rate) * 0.25,
            4,
        )

    @staticmethod
    def _reason(
        category: str,
        base_score: float,
        profile: CategoryStrategyStats | None,
        confidence,
        discovery,
    ) -> str:
        if profile is None or profile.confidence < 0.2:
            return f"Cold start: ranked by {category} match strength"
        if confidence is not None and confidence.exploration_mode:
            return f"Exploration mode: broadening {category} results while confidence is still low"
        if discovery is not None and discovery.career_paths:
            top_category = discovery.career_paths[0].category
            if category == top_category and discovery.career_paths[0].score >= 0.55:
                return f"{category} aligns with the strongest current career discovery signal"
        if profile.success_rate >= 0.35:
            return f"Strong {category} interview and offer history"
        if profile.application_rate >= 0.45:
            return f"High {category} application engagement"
        if profile.rejection_count > profile.interviews_count + profile.offers_count:
            return f"Lower confidence: {category} outcomes need improvement"
        if base_score >= 0.75:
            return f"Strong static match with learned {category} strategy"
        return f"Balanced {category} recommendation using current strategy weights"

    @staticmethod
    def _evidence_strength(profile: CategoryStrategyStats | None) -> float:
        if profile is None:
            return 0.0
        signal_volume = (
            profile.applications_count
            + profile.interviews_count
            + profile.offers_count
            + profile.rejection_count
            + profile.no_response_count
        )
        return round(min(1.0, profile.confidence * 0.65 + min(1.0, signal_volume / 20) * 0.35), 4)

    @staticmethod
    def _explanation(
        *,
        category: str,
        base_score: float,
        behavior_score: float,
        outcome_score: float,
        category_weight: float,
        confidence_score: float,
        profile: CategoryStrategyStats | None,
    ) -> list[str]:
        statements = [
            f"Static match contributed {base_score:.2f} from skills, keywords, experience, and location.",
            f"Learned {category} weight is {category_weight:.2f}; confidence is {confidence_score:.2f}.",
        ]
        if profile is None or profile.confidence < 0.2:
            statements.append("Evidence is sparse, so the engine keeps the ranking close to base match.")
            return statements
        statements.append(
            f"Behavior score is {behavior_score:.2f} from click, application, ignore, and abandonment history."
        )
        statements.append(
            f"Outcome score is {outcome_score:.2f} from interviews, offers, rejections, no responses, and response speed."
        )
        if profile.success_rate >= 0.35:
            statements.append(f"{category} has a strong observed success rate of {profile.success_rate:.2f}.")
        if profile.ignore_rate >= 0.35:
            statements.append(f"{category} has been ignored often, so future ranking is dampened.")
        return statements

    @staticmethod
    def _exploration_bonus(category: str, discovery, confidence_score: float) -> float:
        if discovery is None or not discovery.career_paths:
            return 0.0
        discovered = next(
            (path for path in discovery.career_paths if path.category == category),
            None,
        )
        if discovered is None:
            return 0.0
        return round((1 - confidence_score) * discovered.score * 0.08, 4)

    @staticmethod
    def _repetition_penalty(exposure_count: int) -> float:
        if exposure_count <= 0:
            return 0.0
        return round(min(0.12, exposure_count * 0.02), 4)

    @staticmethod
    def _smoothed_rate(
        numerator: float,
        denominator: float,
        *,
        prior: float,
        strength: float = 4.0,
    ) -> float:
        return round(min(1.0, (numerator + prior * strength) / (denominator + strength)), 4)

    @staticmethod
    def _decay(timestamp: datetime, now: datetime) -> float:
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        age_days = max(0.0, (now - timestamp).total_seconds() / 86400)
        return pow(0.5, age_days / _DECAY_HALF_LIFE_DAYS)

    @staticmethod
    def _empty_profile(user_id: str) -> UserStrategyProfile:
        now = utc_now()
        neutral_profiles = {
            category: CategoryStrategyStats(weight=_NEUTRAL_WEIGHT)
            for category in _CATEGORIES
        }
        neutral_weights = {category: _NEUTRAL_WEIGHT for category in _CATEGORIES}
        neutral_rates = {category: 0.0 for category in _CATEGORIES}
        return UserStrategyProfile(
            user_id=user_id,
            category_weights=neutral_weights,
            category_success_rates=neutral_rates,
            click_rates=neutral_rates,
            application_rates=neutral_rates,
            avg_response_times={category: 0.0 for category in _CATEGORIES},
            category_profiles=neutral_profiles,
            updated_at=now,
        )

    async def _publish(self, channel: str, payload: dict[str, Any]) -> None:
        if self.event_bus is None:
            return
        await self.event_bus.publish(channel, payload)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # V2 Behavioral Intelligence Helper Methods
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def _write_learning_event(
        self,
        behavior: BehaviorEventRecord,
        outcome_event: OutcomeEvent | None = None,
    ) -> None:
        """Write a unified learning event to the immutable store."""
        try:
            antecedent = await self.repository.get_recommendation_event_record(
                behavior.antecedent_event_id,
            )
        except Exception:
            return

        consequence_level = ConsequenceLevel.VIEWED.value
        consequence_weight_val = consequence_weight_for(consequence_level)
        outcome_id = None
        outcome_type = None
        response_time_days = 0.0

        if outcome_event is not None:
            outcome_id = outcome_event.outcome_id
            outcome_type = outcome_event.outcome_type.value
            consequence_level = self._map_outcome_to_consequence(outcome_type)
            consequence_weight_val = consequence_weight_for(consequence_level)
            response_time_days = outcome_event.response_time_days
        else:
            consequence_level = self._map_behavior_to_consequence(behavior.event_type)
            consequence_weight_val = consequence_weight_for(consequence_level)

        signature = " + ".join(filter(None, [
            (antecedent.category or "").strip(),
            " ".join(antecedent.filters_json.get("requirements", [])[:3]) if antecedent.filters_json else "",
        ]))

        now = utc_now()
        strategy = await self.repository.get_user_strategy_profile(behavior.user_id)
        strategy_snapshot = strategy.category_weights if strategy else {}

        try:
            await self.repository.save_abc_learning_event(
                event_id=str(uuid.uuid4()),
                user_id=behavior.user_id,
                timestamp=now,
                job_id=antecedent.job_id or "",
                job_title="",
                job_company="",
                job_category=antecedent.category or "",
                job_location="",
                job_requirements=[],
                goal="",
                hunt_id=antecedent.hunt_id or "",
                session_id=behavior.session_id or "",
                base_match_score=antecedent.base_match_score or 0.0,
                ranking_position=antecedent.rank_position or 0,
                recommendation_reason=antecedent.recommendation_reason or "",
                antecedent_signature=signature,
                behavior_event_id=behavior.id,
                behavior_event_type=behavior.event_type,
                resume_id=behavior.resume_id,
                outcome_id=outcome_id,
                outcome_type=outcome_type,
                consequence_level=consequence_level,
                consequence_weight=consequence_weight_val,
                response_time_days=response_time_days,
                confidence_at_time=0.0,
                strategy_snapshot=strategy_snapshot,
            )
        except Exception:
            logger.warning("Failed to write learning event for behavior %s", behavior.id)

    @staticmethod
    def _map_outcome_to_consequence(outcome_type: str) -> str:
        """Map OutcomeType values to ConsequenceLevel values."""
        mapping = {
            OutcomeType.NO_RESPONSE.value: ConsequenceLevel.IGNORED.value,
            OutcomeType.REJECTION.value: ConsequenceLevel.APPLIED.value,
            OutcomeType.ASSESSMENT.value: ConsequenceLevel.ASSESSMENT.value,
            OutcomeType.INTERVIEW.value: ConsequenceLevel.INTERVIEW.value,
            OutcomeType.FINAL_ROUND.value: ConsequenceLevel.FINAL_ROUND.value,
            OutcomeType.OFFER.value: ConsequenceLevel.OFFER.value,
            OutcomeType.ACCEPTED.value: ConsequenceLevel.ACCEPTED.value,
            OutcomeType.FOLLOW_UP_REQUESTED.value: ConsequenceLevel.APPLIED.value,
        }
        return mapping.get(outcome_type, ConsequenceLevel.VIEWED.value)

    @staticmethod
    def _map_behavior_to_consequence(behavior_type: str) -> str:
        """Map BehaviorEventType to ConsequenceLevel."""
        mapping = {
            BehaviorEventType.VIEW.value: ConsequenceLevel.VIEWED.value,
            BehaviorEventType.CLICK.value: ConsequenceLevel.CLICKED.value,
            BehaviorEventType.SAVE.value: ConsequenceLevel.SAVED.value,
            BehaviorEventType.APPLY.value: ConsequenceLevel.APPLIED.value,
            BehaviorEventType.IGNORE.value: ConsequenceLevel.IGNORED.value,
            BehaviorEventType.ABANDON.value: ConsequenceLevel.IGNORED.value,
        }
        return mapping.get(behavior_type, ConsequenceLevel.VIEWED.value)

    @staticmethod
    def _v2_exploration_bonus(
        category: str,
        discovery,
        confidence_score: float,
        pattern_score: float,
    ) -> float:
        """80/20 exploration/exploitation: 20% of the bonus goes to exploration."""
        if discovery is None or not discovery.career_paths:
            return 0.0
        discovered = next(
            (path for path in discovery.career_paths if path.category == category),
            None,
        )
        if discovered is None:
            return 0.0
        # Scale exploration inversely with pattern confidence
        exploration_weight = max(0.0, 1 - pattern_score) * 0.20
        return round((1 - confidence_score) * discovered.score * exploration_weight, 4)

    @staticmethod
    def _build_job_signature(job: Job) -> str:
        """Build a canonical signature for a job."""
        import re
        parts = []
        location_lower = job.location.lower() if job.location else ""
        if "remote" in location_lower:
            parts.append("remote")
        elif job.location and job.location.strip():
            parts.append(job.location.strip().split(",")[0].strip().lower())

        if job.job_category:
            parts.append(job.job_category.lower())

        title_tokens = re.findall(r"[a-z0-9]+", job.title.lower()) if job.title else []
        stop_words = {"senior", "junior", "lead", "staff", "principal", "engineer", "developer"}
        parts.extend(t for t in title_tokens if t not in stop_words and len(t) > 1)

        for req in (job.requirements or [])[:4]:
            parts.append(req.lower().strip())

        return " + ".join(dict.fromkeys(parts))

    @staticmethod
    def _terms(text: str) -> set[str]:
        """Extract lowercase keyword terms from text."""
        import re
        stop_words = {
            "and", "the", "for", "with", "a", "an", "in", "of", "to",
            "is", "are", "or", "on", "at", "by", "it", "we", "you",
        }
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        return {t for t in tokens if t not in stop_words and len(t) > 1}
