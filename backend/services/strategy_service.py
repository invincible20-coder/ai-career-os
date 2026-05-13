"""
Adaptive strategy selection for hunt execution.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from backend.core.config import Settings
from backend.models.behavior import BehaviorProfile, BehaviorType, StrategyAdjustment
from backend.models.job import Job
from backend.storage.records import utc_now
from backend.services.behavior_service import BehaviorService


@dataclass(slots=True)
class StrategyService:
    """Map behavior profiles to deterministic hunt strategy adjustments."""

    behavior_service: BehaviorService
    settings: Settings

    async def get_strategy(self, user_key: str) -> StrategyAdjustment:
        profile = await self.behavior_service.get_profile(user_key)
        return self.build_strategy(profile)

    def build_strategy(self, profile: BehaviorProfile) -> StrategyAdjustment:
        behavior_type = profile.classification
        max_jobs = self.settings.max_jobs_per_search

        if behavior_type == BehaviorType.HARDCORE:
            return StrategyAdjustment(
                user_key=profile.user_key,
                behavior_type=behavior_type,
                max_applications=min(max_jobs, 3),
                min_fit_score=0.7,
                resume_customization_depth="deep",
                application_frequency="selective",
                explanation="Prioritizing fewer, higher-fit jobs because past conversion is strong.",
                updated_at=utc_now(),
            )

        if behavior_type == BehaviorType.MASS_APPLIER:
            return StrategyAdjustment(
                user_key=profile.user_key,
                behavior_type=behavior_type,
                max_applications=min(max_jobs, 5),
                min_fit_score=0.55,
                resume_customization_depth="targeted",
                application_frequency="filtered",
                explanation="Filtering out low-fit jobs to improve conversion from high-volume activity.",
                updated_at=utc_now(),
            )

        if behavior_type == BehaviorType.PASSIVE:
            return StrategyAdjustment(
                user_key=profile.user_key,
                behavior_type=behavior_type,
                max_applications=max(1, min(max_jobs, 10)),
                min_fit_score=0.3,
                resume_customization_depth="standard",
                application_frequency="increased",
                explanation="Increasing application opportunities because recent activity is low.",
                updated_at=utc_now(),
            )

        if behavior_type == BehaviorType.DESPERATE:
            return StrategyAdjustment(
                user_key=profile.user_key,
                behavior_type=behavior_type,
                max_applications=min(max_jobs, 4),
                min_fit_score=0.6,
                resume_customization_depth="targeted",
                role_similarity_required=True,
                application_frequency="focused",
                explanation="Narrowing role spread and keeping jobs close to the selected goal.",
                updated_at=utc_now(),
            )

        if behavior_type == BehaviorType.NETWORKER:
            return StrategyAdjustment(
                user_key=profile.user_key,
                behavior_type=behavior_type,
                max_applications=min(max_jobs, 6),
                min_fit_score=0.45,
                resume_customization_depth="targeted",
                preferred_platforms=["linkedin"],
                prioritize_referrals=True,
                application_frequency="relationship-led",
                networking_suggestions=[
                    "Prioritize companies with warm introductions.",
                    "Attach a short networking note before applying.",
                ],
                explanation="Biasing toward referral-friendly platforms because referrals convert well.",
                updated_at=utc_now(),
            )

        return StrategyAdjustment(
            user_key=profile.user_key,
            behavior_type=behavior_type,
            max_applications=max(1, min(max_jobs, 6)),
            min_fit_score=0.25,
            resume_customization_depth="standard",
            application_frequency="baseline",
            explanation="Using a balanced baseline strategy until enough behavior data is available.",
            updated_at=utc_now(),
        )

    def search_limit(
        self,
        requested_max_results: int | None,
        strategy: StrategyAdjustment,
    ) -> int:
        requested = requested_max_results or self.settings.max_jobs_per_search
        return max(strategy.max_applications, min(requested, self.settings.max_jobs_per_search))

    def select_jobs(
        self,
        jobs: list[Job],
        *,
        goal: str,
        strategy: StrategyAdjustment,
    ) -> list[Job]:
        if not jobs:
            return []

        candidates = jobs
        if strategy.role_similarity_required:
            similar = [
                job for job in candidates if self._fit_score(job, goal) >= strategy.min_fit_score
            ]
            candidates = similar or candidates

        scored = [
            (
                self._fit_score(job, goal),
                self._referral_rank(job) if strategy.prioritize_referrals else 0,
                self._platform_rank(job, strategy.preferred_platforms),
                job,
            )
            for job in candidates
        ]
        filtered = [item for item in scored if item[0] >= strategy.min_fit_score]
        if not filtered:
            filtered = scored

        filtered.sort(
            key=lambda item: (
                item[1],
                item[2],
                item[0],
                item[3].company.lower(),
            ),
            reverse=True,
        )
        return [item[3] for item in filtered[: strategy.max_applications]]

    def resume_version_for(self, strategy: StrategyAdjustment) -> str:
        return f"{strategy.resume_customization_depth}-v1"

    def is_referral_candidate(self, job: Job) -> bool:
        return self._referral_rank(job) > 0

    @staticmethod
    def _fit_score(job: Job, goal: str) -> float:
        goal_terms = StrategyService._terms(goal)
        haystack_terms = StrategyService._terms(
            " ".join(
                [
                    job.title,
                    job.description,
                    " ".join(job.requirements),
                ]
            )
        )
        if not goal_terms:
            return 0.5
        overlap = len(goal_terms & haystack_terms)
        return round(overlap / len(goal_terms), 4)

    @staticmethod
    def _terms(value: str) -> set[str]:
        stop_words = {"and", "the", "for", "with", "role", "job", "senior"}
        return {
            token
            for token in re.findall(r"[a-z0-9]+", value.lower())
            if token not in stop_words and len(token) > 1
        }

    @staticmethod
    def _referral_rank(job: Job) -> int:
        searchable = " ".join(
            [
                job.source or "",
                job.url or "",
                job.description or "",
            ]
        ).lower()
        if "linkedin" in searchable:
            return 2
        if "referral" in searchable or "employee" in searchable:
            return 1
        return 0

    @staticmethod
    def _platform_rank(job: Job, preferred_platforms: list[str]) -> int:
        source = (job.source or "").lower()
        url = (job.url or "").lower()
        for index, platform in enumerate(preferred_platforms):
            if platform in source or platform in url:
                return len(preferred_platforms) - index
        return 0
