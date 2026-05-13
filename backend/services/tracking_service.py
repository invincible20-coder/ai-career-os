"""
Behavior tracking orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.core.logger import get_logger
from backend.models.behavior import BehaviorProfile
from backend.storage.repository import HuntRepository
from backend.services.behavior_service import BehaviorService

logger = get_logger(__name__)


@dataclass(slots=True)
class TrackingService:
    """Record application behavior snapshots after pipeline activity."""

    repository: HuntRepository
    behavior_service: BehaviorService

    async def refresh_behavior_snapshot(self, user_key: str) -> BehaviorProfile:
        profile = await self.behavior_service.get_profile(user_key)
        await self.repository.save_behavior_snapshot(profile)
        logger.info(
            "behavior_snapshot_saved",
            extra={
                "event": "behavior_snapshot_saved",
                "user_key": user_key,
                "classification": profile.classification.value,
                "total_applications": profile.metrics.total_applications,
                "apps_per_day": profile.metrics.apps_per_day,
                "success_rate": profile.metrics.success_rate,
            },
        )
        return profile
