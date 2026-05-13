"""
FastAPI routes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from backend.models.abc import BehaviorEventCreate, OutcomeCreate, RankJobsRequest
from backend.api.dependencies import get_hunt_service
from backend.api.schemas import (
    CareerRecommendationRequest,
    HealthPayload,
    HuntRequest,
    ResponseEnvelope,
)
from backend.services.hunt_service import HuntService

router = APIRouter()


@router.get("/health", response_model=ResponseEnvelope, tags=["system"])
async def health_check(request: Request) -> ResponseEnvelope:
    settings = request.app.state.settings
    payload = HealthPayload(status="ok", version=settings.app_version)
    return ResponseEnvelope(success=True, data=payload.model_dump(mode="json"), errors=[])


@router.post("/hunts", response_model=ResponseEnvelope, tags=["hunts"])
async def start_hunt(
    http_request: Request,
    payload: HuntRequest,
    service: HuntService = Depends(get_hunt_service),
) -> ResponseEnvelope:
    user_key = _user_key(http_request)
    session_id = _session_id(http_request)
    await service.enforce_hunt_rate_limit(user_key)
    result = await service.start_hunt(
        payload.goal,
        payload,
        user_key=user_key,
        session_id=session_id,
    )
    return ResponseEnvelope(success=True, data=result.model_dump(mode="json"), errors=[])


@router.post("/hunt", response_model=ResponseEnvelope, include_in_schema=False)
async def start_hunt_legacy(
    http_request: Request,
    payload: HuntRequest,
    service: HuntService = Depends(get_hunt_service),
) -> ResponseEnvelope:
    user_key = _user_key(http_request)
    session_id = _session_id(http_request)
    await service.enforce_hunt_rate_limit(user_key)
    result = await service.start_hunt(
        payload.goal,
        payload,
        user_key=user_key,
        session_id=session_id,
    )
    return ResponseEnvelope(success=True, data=result.model_dump(mode="json"), errors=[])


@router.post("/recommend-career", response_model=ResponseEnvelope, tags=["career"])
async def recommend_career(
    payload: CareerRecommendationRequest,
    service: HuntService = Depends(get_hunt_service),
) -> ResponseEnvelope:
    recommendation = await service.recommend_career(payload)
    return ResponseEnvelope(
        success=True,
        data=recommendation.model_dump(mode="json"),
        errors=[],
    )


@router.get("/behavior-profile", response_model=ResponseEnvelope, tags=["behavior"])
async def get_behavior_profile(
    request: Request,
    user_id: str | None = Query(default=None),
    service: HuntService = Depends(get_hunt_service),
) -> ResponseEnvelope:
    profile = await service.get_behavior_profile(_user_key(request, user_id))
    return ResponseEnvelope(
        success=True,
        data=profile.model_dump(mode="json"),
        errors=[],
    )


@router.get("/strategy", response_model=ResponseEnvelope, tags=["behavior"])
async def get_strategy(
    request: Request,
    user_id: str | None = Query(default=None),
    service: HuntService = Depends(get_hunt_service),
) -> ResponseEnvelope:
    strategy = await service.get_strategy(_user_key(request, user_id))
    return ResponseEnvelope(
        success=True,
        data=strategy.model_dump(mode="json"),
        errors=[],
    )


@router.get("/analytics", response_model=ResponseEnvelope, tags=["behavior"])
async def get_analytics(
    request: Request,
    user_id: str | None = Query(default=None),
    service: HuntService = Depends(get_hunt_service),
) -> ResponseEnvelope:
    report = await service.get_analytics(_user_key(request, user_id))
    return ResponseEnvelope(
        success=True,
        data=report.model_dump(mode="json"),
        errors=[],
    )


@router.get("/hunts/{hunt_id}", response_model=ResponseEnvelope, tags=["hunts"])
async def get_hunt(
    hunt_id: str,
    service: HuntService = Depends(get_hunt_service),
) -> ResponseEnvelope:
    result = await service.get_hunt(hunt_id)
    return ResponseEnvelope(success=True, data=result.model_dump(mode="json"), errors=[])


@router.get("/hunts/{hunt_id}/jobs", response_model=ResponseEnvelope, tags=["hunts"])
async def get_jobs(
    hunt_id: str,
    service: HuntService = Depends(get_hunt_service),
) -> ResponseEnvelope:
    jobs = await service.get_jobs(hunt_id)
    return ResponseEnvelope(
        success=True,
        data=[job.model_dump(mode="json") for job in jobs],
        errors=[],
    )


@router.get(
    "/hunts/{hunt_id}/applications",
    response_model=ResponseEnvelope,
    tags=["hunts"],
)
async def get_applications(
    hunt_id: str,
    service: HuntService = Depends(get_hunt_service),
) -> ResponseEnvelope:
    applications = await service.get_applications(hunt_id)
    return ResponseEnvelope(
        success=True,
        data=[application.model_dump(mode="json") for application in applications],
        errors=[],
    )


@router.post("/abc/recommendations", response_model=ResponseEnvelope, tags=["abc"])
async def rank_jobs(
    payload: RankJobsRequest,
    service: HuntService = Depends(get_hunt_service),
) -> ResponseEnvelope:
    ranked = await service.rank_jobs(payload)
    return ResponseEnvelope(success=True, data=ranked.model_dump(mode="json"), errors=[])


@router.post("/abc/behavior-events", response_model=ResponseEnvelope, tags=["abc"])
async def log_behavior_event(
    payload: BehaviorEventCreate,
    service: HuntService = Depends(get_hunt_service),
) -> ResponseEnvelope:
    event = await service.log_behavior_event(payload)
    return ResponseEnvelope(success=True, data=event.model_dump(mode="json"), errors=[])


@router.post("/abc/outcomes", response_model=ResponseEnvelope, tags=["abc"])
async def log_outcome(
    payload: OutcomeCreate,
    service: HuntService = Depends(get_hunt_service),
) -> ResponseEnvelope:
    event = await service.log_outcome(payload)
    return ResponseEnvelope(success=True, data=event.model_dump(mode="json"), errors=[])


@router.get("/abc/strategy-profile", response_model=ResponseEnvelope, tags=["abc"])
async def get_abc_strategy_profile(
    request: Request,
    user_id: str | None = Query(default=None),
    service: HuntService = Depends(get_hunt_service),
) -> ResponseEnvelope:
    profile = await service.get_abc_strategy_profile(_user_key(request, user_id))
    return ResponseEnvelope(success=True, data=profile.model_dump(mode="json"), errors=[])


def _user_key(request: Request, user_id: str | None = None) -> str:
    if user_id and user_id.strip():
        return user_id.strip()
    header_user_id = request.headers.get("x-user-id")
    if header_user_id and header_user_id.strip():
        return header_user_id.strip()
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "anonymous"


def _session_id(request: Request) -> str | None:
    header_session_id = request.headers.get("x-session-id")
    if header_session_id and header_session_id.strip():
        return header_session_id.strip()
    return None
