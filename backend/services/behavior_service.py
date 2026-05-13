"""
Deterministic behavior classification.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.models.behavior import BehaviorMetrics, BehaviorProfile, BehaviorType
from backend.storage.records import utc_now
from backend.services.analytics_service import AnalyticsService


@dataclass(slots=True)
class BehaviorService:
    """Classify users from real application metrics."""

    analytics_service: AnalyticsService

    async def get_profile(self, user_key: str) -> BehaviorProfile:
        metrics = await self.analytics_service.compute_metrics(user_key)
        classification, explanation = self.classify(metrics)
        return BehaviorProfile(
            user_key=user_key,
            classification=classification,
            metrics=metrics,
            explanation=explanation,
            updated_at=utc_now(),
        )

    @staticmethod
    def classify(metrics: BehaviorMetrics) -> tuple[BehaviorType, str]:
        if not metrics.minimum_data_threshold_met:
            return (
                BehaviorType.INSUFFICIENT_DATA,
                "Not enough application history yet for a reliable behavior classification.",
            )

        role_randomness = (
            metrics.role_diversity / metrics.total_applications
            if metrics.total_applications
            else 0
        )

        if metrics.referral_ratio >= 0.3 and metrics.total_applications >= 5:
            return (
                BehaviorType.NETWORKER,
                "A meaningful share of applications are referral-driven.",
            )

        if (
            metrics.apps_per_day >= 10
            and metrics.role_diversity >= 5
            and role_randomness >= 0.45
        ):
            return (
                BehaviorType.DESPERATE,
                "Application volume is high and spread across many distinct roles.",
            )

        if metrics.apps_per_day >= 12 and metrics.success_rate < 0.08:
            return (
                BehaviorType.MASS_APPLIER,
                "Application volume is high while interview or offer conversion is low.",
            )

        if metrics.apps_per_day < 1:
            return (
                BehaviorType.PASSIVE,
                "Application activity is consistently below one application per day.",
            )

        if metrics.apps_per_day < 5 and metrics.success_rate >= 0.2:
            return (
                BehaviorType.HARDCORE,
                "Application volume is selective and conversion is strong.",
            )

        if metrics.apps_per_day >= 8:
            return (
                BehaviorType.MASS_APPLIER,
                "Application volume is elevated and should be filtered more aggressively.",
            )

        if metrics.success_rate >= 0.12:
            return (
                BehaviorType.HARDCORE,
                "Conversion is healthy enough to keep prioritizing fit over volume.",
            )

        return (
            BehaviorType.PASSIVE,
            "Activity is moderate but conversion is not yet strong enough to scale volume.",
        )
