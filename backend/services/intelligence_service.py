"""
Coordinator for intent, discovery, and confidence engines.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.models.career import UserProfile
from backend.models.intelligence import (
    CareerDiscoveryResult,
    ConfidenceEstimate,
    ConversationalIntent,
    UserIntelligenceState,
)
from backend.services.abc_service import ABCAdaptiveService
from backend.services.career_discovery_service import CareerDiscoveryService
from backend.services.confidence_service import ConfidenceService
from backend.services.intent_service import ConversationalIntentService
from backend.storage.records import utc_now
from backend.storage.repository import HuntRepository


@dataclass(slots=True)
class IntelligenceService:
    """Maintains the connected adaptive state for one user."""

    repository: HuntRepository
    abc_service: ABCAdaptiveService
    intent_service: ConversationalIntentService
    discovery_service: CareerDiscoveryService
    confidence_service: ConfidenceService

    async def record_conversation(
        self,
        *,
        user_id: str,
        session_id: str,
        message: str,
        profile: UserProfile | None = None,
    ) -> UserIntelligenceState:
        intent = await self.intent_service.record_turn(
            user_id=user_id,
            session_id=session_id,
            message=message,
            profile=profile,
        )
        return await self.refresh_state(user_id, profile=profile, intent=intent)

    async def get_state(
        self,
        user_id: str,
        *,
        profile: UserProfile | None = None,
    ) -> UserIntelligenceState:
        existing = await self.repository.get_user_intelligence_profile(user_id)
        if existing is not None and profile is None:
            return existing
        return await self.refresh_state(user_id, profile=profile)

    async def refresh_state(
        self,
        user_id: str,
        *,
        profile: UserProfile | None = None,
        intent: ConversationalIntent | None = None,
    ) -> UserIntelligenceState:
        current_intent = intent or await self.intent_service.get_intent(user_id)
        strategy_profile = await self.abc_service.get_strategy_profile(user_id)
        discovery = self.discovery_service.discover(
            intent=current_intent,
            strategy_profile=strategy_profile,
            profile=profile,
        )
        confidence = await self.confidence_service.estimate(
            user_id=user_id,
            profile=profile,
            intent=current_intent,
            discovery=discovery,
            strategy_profile=strategy_profile,
        )
        turns = await self.repository.list_conversation_turns(user_id)
        state = UserIntelligenceState(
            user_id=user_id,
            intent=current_intent,
            discovery=discovery,
            confidence=confidence,
            conversation_count=len(turns),
            updated_at=utc_now(),
        )
        await self.repository.upsert_user_intelligence_profile(state)
        return state

    async def get_intent(self, user_id: str) -> ConversationalIntent:
        return (await self.get_state(user_id)).intent

    async def get_discovery(
        self,
        user_id: str,
        *,
        profile: UserProfile | None = None,
    ) -> CareerDiscoveryResult:
        return (await self.get_state(user_id, profile=profile)).discovery

    async def get_confidence(
        self,
        user_id: str,
        *,
        profile: UserProfile | None = None,
    ) -> ConfidenceEstimate:
        return (await self.get_state(user_id, profile=profile)).confidence
