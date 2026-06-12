"""
Career Persona Inference Engine.

Infers the user's career persona dynamically from ABC behavioral history.
The system NEVER asks the user — it infers through behavior.
The persona continuously evolves as new outcomes arrive.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from backend.models.abc_intelligence import (
    CareerPersona,
    PersonaSnapshot,
    PersonaType,
)
from backend.storage.records import ABCLearningEventRecord, utc_now
from backend.storage.repository import HuntRepository


# Mapping from job categories and keywords to persona types
_PERSONA_SIGNALS: dict[str, dict[str, float]] = {
    PersonaType.BACKEND_BUILDER.value: {
        "backend": 1.0, "api": 0.8, "database": 0.7, "python": 0.5,
        "java": 0.4, "distributed": 0.6, "server": 0.5,
    },
    PersonaType.FRONTEND_CRAFTER.value: {
        "frontend": 1.0, "react": 0.8, "javascript": 0.7, "typescript": 0.7,
        "ui": 0.6, "css": 0.5, "web": 0.4,
    },
    PersonaType.AI_ENGINEER.value: {
        "ai": 1.0, "machine learning": 0.9, "ml": 0.9, "deep learning": 0.8,
        "nlp": 0.7, "pytorch": 0.7, "tensorflow": 0.7, "llm": 0.8,
    },
    PersonaType.ML_RESEARCHER.value: {
        "research": 1.0, "ml": 0.8, "machine learning": 0.8, "papers": 0.6,
        "phd": 0.5, "algorithms": 0.5, "statistics": 0.5,
    },
    PersonaType.DATA_SPECIALIST.value: {
        "data": 1.0, "analytics": 0.8, "sql": 0.6, "etl": 0.7,
        "pipeline": 0.6, "pandas": 0.5, "warehouse": 0.5,
    },
    PersonaType.PLATFORM_ENGINEER.value: {
        "devops": 1.0, "cloud": 0.8, "kubernetes": 0.8, "docker": 0.7,
        "terraform": 0.7, "infrastructure": 0.7, "sre": 0.6,
    },
    PersonaType.MOBILE_DEVELOPER.value: {
        "mobile": 1.0, "android": 0.8, "ios": 0.8, "swift": 0.7,
        "kotlin": 0.7, "react native": 0.6, "flutter": 0.6,
    },
    PersonaType.PRODUCT_DESIGNER.value: {
        "design": 1.0, "ux": 0.9, "figma": 0.7, "visual": 0.6,
        "prototype": 0.6, "user experience": 0.7,
    },
    PersonaType.TECH_LEADER.value: {
        "management": 0.9, "lead": 0.8, "manager": 0.8, "director": 0.7,
        "vp": 0.6, "operations": 0.5, "strategy": 0.5,
    },
}

_CATEGORY_TO_PERSONA: dict[str, str] = {
    "backend": PersonaType.BACKEND_BUILDER.value,
    "frontend": PersonaType.FRONTEND_CRAFTER.value,
    "data": PersonaType.DATA_SPECIALIST.value,
    "devops": PersonaType.PLATFORM_ENGINEER.value,
    "mobile": PersonaType.MOBILE_DEVELOPER.value,
    "design": PersonaType.PRODUCT_DESIGNER.value,
    "management": PersonaType.TECH_LEADER.value,
}


@dataclass(slots=True)
class PersonaService:
    """Infers career persona from behavioral history without asking the user."""

    repository: HuntRepository

    async def infer_persona(self, user_id: str) -> CareerPersona:
        """Derive persona from ABC history and store the result."""
        events = await self.repository.list_abc_learning_events(user_id, limit=500)
        now = utc_now()

        existing = await self.repository.get_career_persona(user_id)
        previous_history: list[PersonaSnapshot] = []
        if existing:
            previous_history = [
                PersonaSnapshot(**snap)
                for snap in existing.evolution_history_json
            ]

        if not events:
            persona = CareerPersona(
                user_id=user_id,
                primary_persona=PersonaType.EXPLORER,
                persona_confidence=0.0,
                persona_scores={p.value: 0.0 for p in PersonaType},
                evolution_history=previous_history,
                updated_at=now,
            )
            await self._persist(persona)
            return persona

        scores = self._compute_persona_scores(events)

        sorted_personas = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary = sorted_personas[0] if sorted_personas else (PersonaType.EXPLORER.value, 0.0)
        secondary = sorted_personas[1] if len(sorted_personas) > 1 else None

        # Confidence based on score separation and data volume
        top_score = primary[1]
        runner_up_score = secondary[1] if secondary else 0.0
        margin = top_score - runner_up_score
        volume_factor = min(1.0, len(events) / 20)
        confidence = round(min(1.0, margin * 0.6 + volume_factor * 0.4), 4)

        # If confidence is too low, keep as Explorer
        if confidence < 0.2 or top_score < 0.1:
            primary_type = PersonaType.EXPLORER
        else:
            primary_type = PersonaType(primary[0])

        secondary_type = PersonaType(secondary[0]) if secondary and secondary[1] > 0.1 else None

        # Update evolution history
        new_snapshot = PersonaSnapshot(
            persona=primary_type,
            confidence=confidence,
            timestamp=now,
        )
        evolution_history = previous_history + [new_snapshot]
        # Keep last 50 snapshots
        evolution_history = evolution_history[-50:]

        persona = CareerPersona(
            user_id=user_id,
            primary_persona=primary_type,
            secondary_persona=secondary_type,
            persona_confidence=confidence,
            persona_scores=scores,
            evolution_history=evolution_history,
            updated_at=now,
        )
        await self._persist(persona)
        return persona

    async def evolve_persona(self, user_id: str) -> CareerPersona:
        """Re-infer persona after new outcomes arrive."""
        return await self.infer_persona(user_id)

    async def get_persona(self, user_id: str) -> CareerPersona:
        """Get current persona, inferring if none exists."""
        existing = await self.repository.get_career_persona(user_id)
        if existing:
            return CareerPersona(
                user_id=existing.user_id,
                primary_persona=PersonaType(existing.primary_persona),
                secondary_persona=PersonaType(existing.secondary_persona) if existing.secondary_persona else None,
                persona_confidence=existing.persona_confidence,
                persona_scores=existing.persona_scores_json,
                evolution_history=[
                    PersonaSnapshot(**snap) for snap in existing.evolution_history_json
                ],
                updated_at=existing.updated_at,
            )
        return await self.infer_persona(user_id)

    def persona_alignment_score(
        self,
        persona: CareerPersona,
        job_category: str,
    ) -> float:
        """How well a job category aligns with the user's inferred persona."""
        if persona.persona_confidence < 0.1:
            return 0.5  # Neutral when unsure

        expected_category = _CATEGORY_TO_PERSONA.get(job_category)
        if expected_category == persona.primary_persona.value:
            return round(0.7 + persona.persona_confidence * 0.3, 4)
        if persona.secondary_persona and expected_category == persona.secondary_persona.value:
            return round(0.5 + persona.persona_confidence * 0.2, 4)

        # Check persona scores for partial match
        persona_score = persona.persona_scores.get(
            expected_category or "", 0.0
        )
        return round(max(0.1, min(0.6, persona_score)), 4)

    def _compute_persona_scores(
        self,
        events: list[ABCLearningEventRecord],
    ) -> dict[str, float]:
        """Compute persona scores from event history."""
        raw_scores: dict[str, float] = defaultdict(float)

        for event in events:
            weight = event.consequence_weight
            if weight <= 0:
                weight = 0.05  # Minimum weight for any event

            # Score from job category
            category = event.job_category
            mapped_persona = _CATEGORY_TO_PERSONA.get(category)
            if mapped_persona:
                raw_scores[mapped_persona] += weight

            # Score from job text keywords
            search_text = " ".join([
                event.job_title,
                " ".join(event.job_requirements_json or []),
            ]).lower()

            for persona_type, signals in _PERSONA_SIGNALS.items():
                for keyword, signal_weight in signals.items():
                    if keyword in search_text:
                        raw_scores[persona_type] += weight * signal_weight * 0.3

        # Normalize to [0, 1]
        max_score = max(raw_scores.values()) if raw_scores else 1.0
        if max_score < 1e-9:
            max_score = 1.0

        return {
            persona.value: round(raw_scores.get(persona.value, 0.0) / max_score, 4)
            for persona in PersonaType
            if persona not in (PersonaType.EXPLORER, PersonaType.GENERALIST)
        }

    async def _persist(self, persona: CareerPersona) -> None:
        """Store persona to database."""
        await self.repository.upsert_career_persona(
            user_id=persona.user_id,
            primary_persona=persona.primary_persona.value,
            secondary_persona=persona.secondary_persona.value if persona.secondary_persona else None,
            persona_confidence=persona.persona_confidence,
            persona_scores=persona.persona_scores,
            evolution_history=[
                snap.model_dump(mode="json") for snap in persona.evolution_history
            ],
        )
