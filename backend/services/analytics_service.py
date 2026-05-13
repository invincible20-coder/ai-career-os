"""
Application analytics derived from persisted tracking records.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from backend.core.config import Settings
from backend.models.behavior import (
    AnalyticsReport,
    ApplicationOutcomeStatus,
    BehaviorMetrics,
    BehaviorType,
)
from backend.storage.records import ApplicationRecord, utc_now
from backend.storage.repository import HuntRepository

SUCCESS_STATUSES = {
    ApplicationOutcomeStatus.INTERVIEW.value,
    ApplicationOutcomeStatus.OFFER.value,
}


@dataclass(slots=True)
class AnalyticsService:
    """Compute behavior metrics from durable application history."""

    repository: HuntRepository
    settings: Settings

    async def compute_metrics(self, user_key: str) -> BehaviorMetrics:
        records = await self.repository.list_application_records(
            user_key,
            window_days=self.settings.behavior_analysis_window_days,
        )
        return self._compute_from_records(user_key, records)

    async def build_report(
        self,
        user_key: str,
        classification: BehaviorType,
    ) -> AnalyticsReport:
        metrics = await self.compute_metrics(user_key)
        return AnalyticsReport(
            user_key=user_key,
            metrics=metrics,
            classification=classification,
            top_platforms=self._top_items(metrics.platform_distribution),
            top_roles=self._top_items(metrics.role_distribution),
            best_resume_versions=self._top_float_items(metrics.resume_success_rate),
            generated_at=utc_now(),
        )

    def _compute_from_records(
        self,
        user_key: str,
        records: list[ApplicationRecord],
    ) -> BehaviorMetrics:
        total = len(records)
        now = utc_now()
        if total == 0:
            return BehaviorMetrics(
                user_key=user_key,
                analysis_window_days=self.settings.behavior_analysis_window_days,
                computed_at=now,
            )

        timestamps = [record.timestamp_applied for record in records]
        first_seen = min(timestamps)
        last_seen = max(timestamps)
        observed_seconds = max((last_seen - first_seen).total_seconds(), 0)
        observed_days = max(1.0, observed_seconds / 86_400 + 1)

        successes = sum(
            1 for record in records if record.application_status in SUCCESS_STATUSES
        )
        platform_distribution = Counter(
            self._normalise_label(record.platform or "unknown") for record in records
        )
        role_distribution = Counter(
            self._normalise_role(record.role or record.job_title) for record in records
        )
        referral_count = sum(1 for record in records if record.is_referral)
        resume_success_rate = self._resume_success_rates(records)

        return BehaviorMetrics(
            user_key=user_key,
            total_applications=total,
            analysis_window_days=self.settings.behavior_analysis_window_days,
            observed_days=round(observed_days, 2),
            apps_per_day=round(total / observed_days, 2),
            success_rate=round(successes / total, 4),
            platform_distribution=dict(platform_distribution),
            role_diversity=len(role_distribution),
            role_distribution=dict(role_distribution),
            resume_success_rate=resume_success_rate,
            referral_ratio=round(referral_count / total, 4),
            minimum_data_threshold_met=total >= self.settings.behavior_min_applications,
            computed_at=now,
        )

    @staticmethod
    def _resume_success_rates(
        records: list[ApplicationRecord],
    ) -> dict[str, float]:
        totals: dict[str, int] = defaultdict(int)
        successes: dict[str, int] = defaultdict(int)
        for record in records:
            version = record.resume_version or "standard-v1"
            totals[version] += 1
            if record.application_status in SUCCESS_STATUSES:
                successes[version] += 1
        return {
            version: round(successes[version] / count, 4)
            for version, count in totals.items()
        }

    @staticmethod
    def _normalise_label(value: str) -> str:
        return " ".join(value.strip().lower().split()) or "unknown"

    @staticmethod
    def _normalise_role(value: str) -> str:
        cleaned = " ".join(value.strip().lower().split())
        for suffix in (" engineer", " developer", " specialist"):
            if cleaned.endswith(suffix):
                return cleaned.removesuffix(suffix).strip() or cleaned
        return cleaned or "unknown"

    @staticmethod
    def _top_items(distribution: dict[str, int]) -> list[dict[str, int]]:
        return [
            {"name": name, "count": count}
            for name, count in sorted(
                distribution.items(),
                key=lambda item: (-item[1], item[0]),
            )[:5]
        ]

    @staticmethod
    def _top_float_items(distribution: dict[str, float]) -> list[dict[str, float]]:
        return [
            {"name": name, "rate": rate}
            for name, rate in sorted(
                distribution.items(),
                key=lambda item: (-item[1], item[0]),
            )[:5]
        ]
