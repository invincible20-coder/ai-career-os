"""
Service layer that exposes hunt operations to the API.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.models.behavior import AnalyticsReport, BehaviorProfile, StrategyAdjustment
from backend.models.abc import (
    BehaviorEvent,
    BehaviorEventCreate,
    OutcomeCreate,
    OutcomeEvent,
    RankJobsResponse,
    RankJobsRequest,
    UserStrategyProfile,
)
from backend.models.application import Application
from backend.models.career import CareerRecommendation, UserProfile
from backend.models.hunt import HuntResult
from backend.models.job import Job
from backend.orchestrator import HuntOrchestrator
from backend.services.analytics_service import AnalyticsService
from backend.services.behavior_service import BehaviorService
from backend.services.abc_service import ABCAdaptiveService
from backend.services.strategy_service import StrategyService
from backend.storage.repository import HuntRepository


@dataclass(slots=True)
class HuntService:
    """API-facing service methods."""

    repository: HuntRepository
    orchestrator: HuntOrchestrator
    analytics_service: AnalyticsService
    behavior_service: BehaviorService
    strategy_service: StrategyService
    abc_service: ABCAdaptiveService

    async def start_hunt(
        self,
        goal: str | None,
        profile: UserProfile,
        *,
        user_key: str,
        session_id: str | None = None,
    ) -> HuntResult:
        return await self.orchestrator.execute(
            goal,
            profile,
            user_key=user_key,
            session_id=session_id,
        )

    async def enforce_hunt_rate_limit(self, client_key: str) -> None:
        await self.repository.consume_rate_limit(
            client_key=client_key,
            route_key="hunts",
            max_requests=self.orchestrator.settings.hunt_rate_limit_requests,
            window_seconds=self.orchestrator.settings.hunt_rate_limit_window_seconds,
        )

    async def recommend_career(self, profile: UserProfile) -> CareerRecommendation:
        return await self.orchestrator.recommend_career(profile)

    async def get_behavior_profile(self, user_key: str) -> BehaviorProfile:
        return await self.behavior_service.get_profile(user_key)

    async def get_strategy(self, user_key: str) -> StrategyAdjustment:
        return await self.strategy_service.get_strategy(user_key)

    async def get_analytics(self, user_key: str) -> AnalyticsReport:
        profile = await self.behavior_service.get_profile(user_key)
        return await self.analytics_service.build_report(user_key, profile.classification)

    async def get_hunt(self, hunt_id: str) -> HuntResult:
        return await self.repository.get_hunt_result(hunt_id)

    async def get_jobs(self, hunt_id: str) -> list[Job]:
        return await self.repository.get_jobs_for_hunt(hunt_id)

    async def get_applications(self, hunt_id: str) -> list[Application]:
        return await self.repository.get_applications_for_hunt(hunt_id)

    async def rank_jobs(self, request: RankJobsRequest) -> RankJobsResponse:
        hunt_id = request.hunt_id or f"adhoc-{request.user_id}"
        session_id = request.session_id or hunt_id
        ranked = await self.abc_service.rank_jobs(
            user_id=request.user_id,
            hunt_id=hunt_id,
            session_id=session_id,
            goal=request.goal,
            jobs=request.jobs,
            filters=request.filters,
        )
        return RankJobsResponse(
            user_id=request.user_id,
            hunt_id=hunt_id,
            session_id=session_id,
            recommendations=ranked,
        )

    async def log_behavior_event(self, payload: BehaviorEventCreate) -> BehaviorEvent:
        return await self.abc_service.log_behavior(payload)

    async def log_outcome(self, payload: OutcomeCreate) -> OutcomeEvent:
        return await self.abc_service.log_outcome(payload)

    async def get_abc_strategy_profile(self, user_id: str) -> UserStrategyProfile:
        return await self.abc_service.refresh_strategy_profile(user_id)
