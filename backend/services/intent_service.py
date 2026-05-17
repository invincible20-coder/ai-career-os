"""
Deterministic conversational intent engine with persisted rolling memory.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from backend.models.career import UserProfile
from backend.models.intelligence import ConversationTurn, ConversationalIntent
from backend.storage.records import utc_now
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


@dataclass(slots=True)
class ConversationalIntentService:
    """Infers vague human intent and remembers how it evolves."""

    repository: HuntRepository

    async def record_turn(
        self,
        *,
        user_id: str,
        session_id: str,
        message: str,
        profile: UserProfile | None = None,
    ) -> ConversationalIntent:
        previous_state = await self.repository.get_user_intelligence_profile(user_id)
        previous_intent = previous_state.intent if previous_state else self._neutral_intent()
        current_signals, current_categories, reasons = self._extract_turn_signals(
            message,
            profile,
        )
        intent = self._blend_intent(
            previous_intent,
            current_signals,
            current_categories,
            reasons,
        )
        await self.repository.save_conversation_turn(
            ConversationTurn(
                turn_id=str(uuid.uuid4()),
                user_id=user_id,
                session_id=session_id,
                message=message,
                extracted_signals=current_signals,
                category_preferences=current_categories,
                created_at=intent.updated_at,
            )
        )
        return intent

    async def get_intent(self, user_id: str) -> ConversationalIntent:
        state = await self.repository.get_user_intelligence_profile(user_id)
        if state is not None:
            return state.intent

        turns = await self.repository.list_conversation_turns(user_id)
        if not turns:
            return self._neutral_intent()

        intent = self._neutral_intent()
        for turn in turns:
            intent = self._blend_intent(
                intent,
                turn.extracted_signals,
                turn.category_preferences,
                [],
            )
        return intent

    @staticmethod
    def _extract_turn_signals(
        message: str,
        profile: UserProfile | None,
    ) -> tuple[dict[str, float], dict[str, float], list[str]]:
        text = message.lower()
        reasons: list[str] = []

        uncertainty_terms = {
            "dont know",
            "don't know",
            "not sure",
            "confused",
            "lost",
            "maybe",
            "any role",
            "anything",
        }
        urgency_terms = {"urgent", "asap", "immediately", "quickly", "need a job", "soon"}
        frustration_terms = {
            "anymore",
            "frustrated",
            "tired",
            "nothing works",
            "stuck",
            "rejected",
        }
        curiosity_terms = {"curious", "explore", "maybe", "interested", "learn"}
        commitment_terms = {"want to", "plan to", "committed", "focus on", "target", "decided"}
        technical_terms = {
            "api",
            "backend",
            "frontend",
            "python",
            "java",
            "system",
            "database",
            "cloud",
            "data",
            "machine learning",
            "react",
        }

        uncertainty = ConversationalIntentService._contains_ratio(text, uncertainty_terms, 2)
        urgency = ConversationalIntentService._contains_ratio(text, urgency_terms, 2)
        frustration = ConversationalIntentService._contains_ratio(text, frustration_terms, 2)
        curiosity = ConversationalIntentService._contains_ratio(text, curiosity_terms, 2)
        commitment = ConversationalIntentService._contains_ratio(text, commitment_terms, 2)
        technical_interest = ConversationalIntentService._contains_ratio(text, technical_terms, 3)

        if uncertainty:
            reasons.append("The user expressed uncertainty about direction")
        if urgency:
            reasons.append("The user signaled urgency")
        if frustration:
            reasons.append("The user expressed frustration")
        if curiosity:
            reasons.append("The user showed exploratory curiosity")
        if technical_interest:
            reasons.append("The conversation contains technical-role signals")

        categories = ConversationalIntentService._category_preferences(text, profile)
        strongest_category = max(categories, key=categories.get)
        category_strength = categories[strongest_category]
        career_clarity = max(0.0, min(1.0, category_strength * 0.8 + commitment * 0.2))
        if uncertainty:
            career_clarity = max(0.0, career_clarity - uncertainty * 0.45)

        return (
            {
                "career_clarity": round(career_clarity, 4),
                "technical_interest": round(technical_interest, 4),
                "urgency": round(urgency, 4),
                "uncertainty": round(uncertainty, 4),
                "frustration": round(frustration, 4),
                "curiosity": round(curiosity, 4),
                "commitment_level": round(commitment, 4),
            },
            categories,
            reasons,
        )

    @staticmethod
    def _blend_intent(
        previous: ConversationalIntent,
        current_signals: dict[str, float],
        current_categories: dict[str, float],
        reasons: list[str],
    ) -> ConversationalIntent:
        now = utc_now()
        blended = {
            key: round(
                getattr(previous, key) * 0.65 + current_signals.get(key, 0.0) * 0.35,
                4,
            )
            for key in (
                "career_clarity",
                "technical_interest",
                "urgency",
                "uncertainty",
                "frustration",
                "curiosity",
                "commitment_level",
            )
        }
        categories = {
            category: round(
                previous.category_preferences.get(category, 1 / len(_CATEGORIES)) * 0.65
                + current_categories.get(category, 0.0) * 0.35,
                4,
            )
            for category in _CATEGORIES
        }
        total = sum(categories.values()) or 1.0
        categories = {
            category: round(value / total, 4)
            for category, value in categories.items()
        }
        exploration_mode = bool(
            blended["career_clarity"] < 0.55
            or blended["uncertainty"] > 0.35
            or blended["curiosity"] > 0.55
        )
        return ConversationalIntent(
            **blended,
            exploration_mode=exploration_mode,
            category_preferences=categories,
            reasons=reasons or previous.reasons,
            updated_at=now,
        )

    @staticmethod
    def _category_preferences(
        text: str,
        profile: UserProfile | None,
    ) -> dict[str, float]:
        profile_terms = " ".join(
            [
                *(profile.skills if profile else []),
                *(profile.interests if profile else []),
                *(profile.github_topics if profile else []),
                *(profile.learning_history if profile else []),
                profile.education or "" if profile else "",
                profile.experience or "" if profile else "",
            ]
        ).lower()
        combined = f"{text} {profile_terms}"
        keywords = {
            "backend": {"backend", "api", "python", "database", "distributed", "server"},
            "frontend": {"frontend", "react", "javascript", "typescript", "ui", "web"},
            "data": {"data", "analytics", "sql", "pandas", "machine learning", "ml"},
            "devops": {"devops", "cloud", "docker", "kubernetes", "infrastructure"},
            "mobile": {"mobile", "android", "ios", "swift", "kotlin"},
            "design": {"design", "ux", "figma", "visual", "product design"},
            "management": {"management", "manager", "lead", "operations", "program"},
            "non_technical": {"sales", "marketing", "support", "business", "recruiting"},
        }
        raw = {
            category: sum(1 for keyword in category_keywords if keyword in combined)
            for category, category_keywords in keywords.items()
        }
        raw["general"] = 1
        total = sum(raw.values()) or 1
        return {
            category: round(raw.get(category, 0) / total, 4)
            for category in _CATEGORIES
        }

    @staticmethod
    def _contains_ratio(text: str, terms: set[str], saturation: int) -> float:
        hits = sum(1 for term in terms if term in text)
        return round(min(1.0, hits / saturation), 4)

    @staticmethod
    def _neutral_intent() -> ConversationalIntent:
        now = utc_now()
        neutral_categories = {category: round(1 / len(_CATEGORIES), 4) for category in _CATEGORIES}
        return ConversationalIntent(
            career_clarity=0.2,
            technical_interest=0.2,
            urgency=0.0,
            uncertainty=0.5,
            frustration=0.0,
            curiosity=0.3,
            commitment_level=0.1,
            exploration_mode=True,
            category_preferences=neutral_categories,
            reasons=["Insufficient conversational history"],
            updated_at=now,
        )
