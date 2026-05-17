"""
FastAPI dependency providers.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.orchestrator import HuntOrchestrator
from backend.services.analytics_service import AnalyticsService
from backend.services.behavior_service import BehaviorService
from backend.services.abc_service import ABCAdaptiveService
from backend.services.career_discovery_service import CareerDiscoveryService
from backend.services.confidence_service import ConfidenceService
from backend.services.hunt_service import HuntService
from backend.services.intelligence_service import IntelligenceService
from backend.services.intent_service import ConversationalIntentService
from backend.services.predictive_career_service import PredictiveCareerService
from backend.services.resume_correlation_service import ResumeCorrelationService
from backend.services.strategy_service import StrategyService
from backend.services.tracking_service import TrackingService
from backend.storage.repository import HuntRepository


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped async database session."""

    session_factory = request.app.state.db.session_factory
    async with session_factory() as session:
        try:
            yield session
        finally:
            if session.in_transaction():
                await session.rollback()


async def get_hunt_service(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> HuntService:
    """Build a request-scoped service instance."""

    repository = HuntRepository(session)
    analytics_service = AnalyticsService(repository, request.app.state.settings)
    behavior_service = BehaviorService(analytics_service)
    strategy_service = StrategyService(behavior_service, request.app.state.settings)
    tracking_service = TrackingService(repository, behavior_service)
    confidence_service = ConfidenceService(repository)
    discovery_service = CareerDiscoveryService()
    intent_service = ConversationalIntentService(repository)
    resume_correlation_service = ResumeCorrelationService(repository)
    abc_service = ABCAdaptiveService(
        repository,
        confidence_service=confidence_service,
        discovery_service=discovery_service,
    )
    intelligence_service = IntelligenceService(
        repository=repository,
        abc_service=abc_service,
        intent_service=intent_service,
        discovery_service=discovery_service,
        confidence_service=confidence_service,
    )
    predictive_career_service = PredictiveCareerService(
        repository=repository,
        abc_service=abc_service,
        resume_service=resume_correlation_service,
    )
    orchestrator = HuntOrchestrator(
        repository=repository,
        agents=request.app.state.agents,
        settings=request.app.state.settings,
        strategy_service=strategy_service,
        tracking_service=tracking_service,
        abc_service=abc_service,
        resume_correlation_service=resume_correlation_service,
    )
    return HuntService(
        repository=repository,
        orchestrator=orchestrator,
        analytics_service=analytics_service,
        behavior_service=behavior_service,
        strategy_service=strategy_service,
        abc_service=abc_service,
        intelligence_service=intelligence_service,
        resume_correlation_service=resume_correlation_service,
        predictive_career_service=predictive_career_service,
    )
