"""
Strategy Feedback Loop — ABC ↔ Strategy Engine bidirectional signals.

Analyzes application-to-interview ratios, detects resume weakness vs strong fit,
and generates actionable strategy adjustment signals.

Example:
  Many Applications + Low Interviews → Signal: RESUME_WEAKNESS → Strategy: Improve Resume
  High Interview Rate → Signal: STRONG_FIT → Strategy: Increase Application Volume
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from backend.models.abc import UserStrategyProfile
from backend.models.abc_intelligence import (
    StrategyFeedbackSignal,
    StrategySignalType,
)
from backend.storage.records import utc_now
from backend.storage.repository import HuntRepository


@dataclass(slots=True)
class StrategyFeedbackService:
    """Generates strategy signals from ABC behavioral patterns."""

    repository: HuntRepository

    async def generate_signals(
        self,
        user_id: str,
        strategy_profile: UserStrategyProfile,
    ) -> list[StrategyFeedbackSignal]:
        """Analyze the strategy profile and generate actionable signals."""
        now = utc_now()
        signals: list[StrategyFeedbackSignal] = []

        for category, profile in strategy_profile.category_profiles.items():
            if profile.confidence < 0.2:
                continue  # Not enough data

            category_signals = self._analyze_category(category, profile, now)
            signals.extend(category_signals)

        # Cross-category signals
        cross_signals = self._cross_category_signals(strategy_profile, now)
        signals.extend(cross_signals)

        return signals

    async def recommend_strategy_adjustments(
        self,
        user_id: str,
    ) -> list[StrategyFeedbackSignal]:
        """Full pipeline: load profile, analyze, return signals."""
        from backend.services.abc_service import ABCAdaptiveService

        profile = await self.repository.get_user_strategy_profile(user_id)
        if profile is None:
            return []

        strategy_profile = UserStrategyProfile(
            user_id=user_id,
            category_weights=profile.category_weights,
            category_success_rates=profile.category_success_rates,
            click_rates=profile.click_rates,
            application_rates=profile.application_rates,
            avg_response_times=profile.avg_response_times,
            category_profiles=profile.category_profiles,
            updated_at=profile.updated_at,
        )
        return await self.generate_signals(user_id, strategy_profile)

    @staticmethod
    def _analyze_category(category: str, profile, now: datetime) -> list[StrategyFeedbackSignal]:
        """Analyze a single category for strategy signals."""
        signals: list[StrategyFeedbackSignal] = []

        applications = profile.applications_count
        interviews = profile.interviews_count
        offers = profile.offers_count
        rejections = profile.rejection_count
        no_responses = profile.no_response_count

        if applications <= 0:
            return signals

        interview_rate = interviews / applications
        offer_rate = offers / max(1, interviews) if interviews else 0.0
        rejection_rate = (rejections + no_responses) / applications

        # RESUME WEAKNESS: Many applications, few interviews
        if applications >= 5 and interview_rate < 0.15:
            signals.append(
                StrategyFeedbackSignal(
                    signal_id=str(uuid.uuid4()),
                    user_id="",  # filled by caller
                    signal_type=StrategySignalType.RESUME_WEAKNESS,
                    category=category,
                    strength=round(min(1.0, (1 - interview_rate) * 0.8), 4),
                    evidence=[
                        f"{applications} applications with only {interviews} interviews ({interview_rate:.0%})",
                        f"Rejection/no-response rate: {rejection_rate:.0%}",
                    ],
                    recommended_action=f"Improve resume targeting for {category} roles. Consider reformatting or adding relevant {category} keywords.",
                    created_at=now,
                )
            )

        # STRONG FIT: High interview rate
        if applications >= 3 and interview_rate >= 0.40:
            signals.append(
                StrategyFeedbackSignal(
                    signal_id=str(uuid.uuid4()),
                    user_id="",
                    signal_type=StrategySignalType.STRONG_FIT,
                    category=category,
                    strength=round(min(1.0, interview_rate), 4),
                    evidence=[
                        f"{interview_rate:.0%} interview rate from {applications} applications",
                        f"Offer rate: {offer_rate:.0%}",
                    ],
                    recommended_action=f"Increase application volume in {category}. Current approach is working well.",
                    created_at=now,
                )
            )

        # INCREASE VOLUME: Good interviews but few applications
        if interviews >= 2 and applications < 5:
            signals.append(
                StrategyFeedbackSignal(
                    signal_id=str(uuid.uuid4()),
                    user_id="",
                    signal_type=StrategySignalType.INCREASE_VOLUME,
                    category=category,
                    strength=round(min(1.0, interview_rate * 0.7), 4),
                    evidence=[
                        f"Only {applications} applications but {interviews} interviews",
                        "More applications could yield more offers",
                    ],
                    recommended_action=f"Apply to more {category} roles. Your conversion rate supports higher volume.",
                    created_at=now,
                )
            )

        # IMPROVE TARGETING: High application rate but low interviews
        if applications >= 8 and interview_rate < 0.10 and profile.click_rate > 0.3:
            signals.append(
                StrategyFeedbackSignal(
                    signal_id=str(uuid.uuid4()),
                    user_id="",
                    signal_type=StrategySignalType.IMPROVE_TARGETING,
                    category=category,
                    strength=round(min(1.0, 1 - interview_rate), 4),
                    evidence=[
                        f"High click rate ({profile.click_rate:.0%}) but low interview rate ({interview_rate:.0%})",
                        "Jobs are interesting but applications aren't converting",
                    ],
                    recommended_action=f"Narrow {category} applications to better-fitting roles. Focus on jobs that match your strongest skills.",
                    created_at=now,
                )
            )

        return signals

    @staticmethod
    def _cross_category_signals(
        strategy_profile: UserStrategyProfile,
        now: datetime,
    ) -> list[StrategyFeedbackSignal]:
        """Analyze cross-category patterns for signals."""
        signals: list[StrategyFeedbackSignal] = []

        # Find categories with high success and suggest exploring adjacent ones
        successful_categories = []
        for category, profile in strategy_profile.category_profiles.items():
            if profile.success_rate >= 0.3 and profile.applications_count >= 3:
                successful_categories.append(category)

        if successful_categories:
            adjacent_map = {
                "backend": ["devops", "data"],
                "frontend": ["mobile", "design"],
                "data": ["backend", "devops"],
                "devops": ["backend", "data"],
                "mobile": ["frontend"],
                "design": ["frontend"],
                "management": ["backend", "devops"],
            }
            explored_categories = {
                cat for cat, prof in strategy_profile.category_profiles.items()
                if prof.applications_count >= 2
            }
            for category in successful_categories:
                adjacent = adjacent_map.get(category, [])
                unexplored = [a for a in adjacent if a not in explored_categories]
                if unexplored:
                    signals.append(
                        StrategyFeedbackSignal(
                            signal_id=str(uuid.uuid4()),
                            user_id="",
                            signal_type=StrategySignalType.EXPLORE_ADJACENT,
                            category=category,
                            strength=0.5,
                            evidence=[
                                f"Strong success in {category}",
                                f"Adjacent categories to explore: {', '.join(unexplored)}",
                            ],
                            recommended_action=f"Consider exploring {', '.join(unexplored)} roles based on your {category} success.",
                            created_at=now,
                        )
                    )

        # NARROW FOCUS: Spreading too thin across many categories
        active_categories = [
            cat for cat, prof in strategy_profile.category_profiles.items()
            if prof.applications_count >= 2
        ]
        if len(active_categories) >= 5:
            best = max(
                active_categories,
                key=lambda c: strategy_profile.category_profiles[c].success_rate,
            )
            signals.append(
                StrategyFeedbackSignal(
                    signal_id=str(uuid.uuid4()),
                    user_id="",
                    signal_type=StrategySignalType.NARROW_FOCUS,
                    category=best,
                    strength=0.6,
                    evidence=[
                        f"Applications spread across {len(active_categories)} categories",
                        f"Best success in {best}",
                    ],
                    recommended_action=f"Consider narrowing focus to {best} and closely related categories.",
                    created_at=now,
                )
            )

        return signals
