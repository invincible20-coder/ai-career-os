"""
Ambiguity-preserving career discovery engine.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.models.abc import UserStrategyProfile
from backend.models.career import UserProfile
from backend.models.intelligence import CareerDiscoveryResult, CareerPathSuggestion, ConversationalIntent
from backend.storage.records import utc_now


_ROLE_BY_CATEGORY = {
    "backend": "Backend Engineer",
    "frontend": "Frontend Engineer",
    "data": "Data Analyst",
    "devops": "Platform Engineer",
    "mobile": "Mobile Engineer",
    "design": "Product Designer",
    "management": "Technical Program Manager",
    "non_technical": "Business Analyst",
    "general": "Software Engineer",
}

_CATEGORY_KEYWORDS = {
    "backend": {"backend", "api", "python", "database", "distributed", "server"},
    "frontend": {"frontend", "react", "javascript", "typescript", "ui", "web"},
    "data": {"data", "analytics", "sql", "pandas", "machine learning", "ml"},
    "devops": {"devops", "cloud", "docker", "kubernetes", "terraform"},
    "mobile": {"mobile", "android", "ios", "swift", "kotlin"},
    "design": {"design", "ux", "figma", "visual"},
    "management": {"management", "manager", "lead", "operations", "program"},
    "non_technical": {"sales", "marketing", "support", "business", "recruiting"},
    "general": {"software", "engineering", "technology"},
}


@dataclass(slots=True)
class CareerDiscoveryService:
    """Combines intent, profile, and outcomes into career hypotheses."""

    def discover(
        self,
        *,
        intent: ConversationalIntent,
        strategy_profile: UserStrategyProfile,
        profile: UserProfile | None = None,
    ) -> CareerDiscoveryResult:
        profile_text = self._profile_text(profile)
        scores: dict[str, float] = {}
        reasons: dict[str, str] = {}

        for category, role in _ROLE_BY_CATEGORY.items():
            category_profile = strategy_profile.category_profiles.get(category)
            behavioral_alignment = self._behavioral_alignment(
                category,
                intent,
                strategy_profile,
            )
            skill_match = self._skill_match(category, profile_text)
            engagement_score = self._engagement_score(category_profile)
            outcome_alignment = self._outcome_alignment(category_profile)
            score = round(
                behavioral_alignment * 0.40
                + skill_match * 0.30
                + engagement_score * 0.20
                + outcome_alignment * 0.10,
                4,
            )
            scores[category] = score
            reasons[category] = self._reason(
                category,
                behavioral_alignment,
                skill_match,
                outcome_alignment,
            )

        ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        top_score = ordered[0][1] if ordered else 0.0
        runner_up = ordered[1][1] if len(ordered) > 1 else 0.0
        margin = max(0.0, top_score - runner_up)
        ambiguity_score = round(max(0.0, min(1.0, 1 - margin * 2)), 4)
        exploration_mode = bool(intent.exploration_mode or ambiguity_score >= 0.55)

        max_paths = 4 if exploration_mode else 3
        career_paths = [
            CareerPathSuggestion(
                role=_ROLE_BY_CATEGORY[category],
                category=category,
                score=score,
                reason=reasons[category],
            )
            for category, score in ordered[:max_paths]
        ]

        global_reasons = [
            "Multiple career paths remain plausible"
            if exploration_mode
            else "One direction currently has a clearer lead",
            "Conversational and behavioral evidence are blended before narrowing options",
        ]
        return CareerDiscoveryResult(
            career_paths=career_paths,
            ambiguity_score=ambiguity_score,
            exploration_mode=exploration_mode,
            reasons=global_reasons,
            updated_at=utc_now(),
        )

    @staticmethod
    def _behavioral_alignment(
        category: str,
        intent: ConversationalIntent,
        strategy_profile: UserStrategyProfile,
    ) -> float:
        intent_weight = intent.category_preferences.get(category, 0.0)
        learned_weight = strategy_profile.category_weights.get(category, 0.5)
        return round(intent_weight * 0.55 + learned_weight * 0.45, 4)

    @staticmethod
    def _skill_match(category: str, profile_text: str) -> float:
        if not profile_text:
            return 0.5
        keywords = _CATEGORY_KEYWORDS[category]
        hits = sum(1 for keyword in keywords if keyword in profile_text)
        return round(min(1.0, hits / max(1, min(4, len(keywords)))), 4)

    @staticmethod
    def _engagement_score(category_profile) -> float:
        if category_profile is None:
            return 0.5
        return round(
            category_profile.click_rate * 0.45
            + category_profile.application_rate * 0.40
            + (1 - category_profile.abandonment_rate) * 0.15,
            4,
        )

    @staticmethod
    def _outcome_alignment(category_profile) -> float:
        if category_profile is None:
            return 0.5
        response_speed = min(1.0, 1 / max(category_profile.avg_response_time, 1.0))
        return round(
            category_profile.success_rate * 0.70
            + response_speed * 0.30,
            4,
        )

    @staticmethod
    def _reason(
        category: str,
        behavioral_alignment: float,
        skill_match: float,
        outcome_alignment: float,
    ) -> str:
        if outcome_alignment >= 0.6:
            return f"{category} has strong outcome alignment"
        if skill_match >= 0.6:
            return f"{category} matches the current profile signals"
        if behavioral_alignment >= 0.45:
            return f"{category} remains behaviorally plausible"
        return f"{category} stays in exploration because evidence is still sparse"

    @staticmethod
    def _profile_text(profile: UserProfile | None) -> str:
        if profile is None:
            return ""
        return " ".join(
            [
                *profile.skills,
                *profile.interests,
                *profile.github_topics,
                *profile.learning_history,
                profile.education or "",
                profile.experience or "",
            ]
        ).lower()
