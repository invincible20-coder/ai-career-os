"""
Request-safe orchestrator implementation.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from time import perf_counter
from typing import Awaitable, Callable, TypeVar

from backend.agents import AgentSuite
from backend.core.config import Settings
from backend.core.logger import get_logger
from backend.models.abc import RankedJob
from backend.models.application import Application
from backend.models.behavior import StrategyAdjustment
from backend.models.career import CareerRecommendation, UserProfile
from backend.models.errors import ErrorDetail
from backend.models.hunt import HuntResult
from backend.models.job import Job, JobSearchResult
from backend.models.plan import ExecutionPlan, StepType
from backend.services.exceptions import (
    BadRequestError,
    PipelineExecutionError,
    PlanValidationError,
    ServiceError,
    StepExecutionError,
)
from backend.services.plan_validator import validate_execution_plan
from backend.services.retry import backoff_seconds, is_transient_error
from backend.services.abc_service import ABCAdaptiveService
from backend.services.event_bus import EventBus
from backend.services.resume_correlation_service import ResumeCorrelationService
from backend.services.strategy_service import StrategyService
from backend.services.tracking_service import TrackingService
from backend.storage.repository import HuntRepository

logger = get_logger(__name__)
T = TypeVar("T")

# Maximum wall-clock time for any single pipeline step (plan, search, apply, track)
STEP_TIMEOUT_SECONDS = 90


@dataclass(slots=True)
class HuntOrchestrator:
    """Coordinates the full hunt pipeline for one request."""

    repository: HuntRepository
    agents: AgentSuite
    settings: Settings
    strategy_service: StrategyService
    tracking_service: TrackingService
    abc_service: ABCAdaptiveService
    resume_correlation_service: ResumeCorrelationService
    event_bus: EventBus | None = None

    async def execute(
        self,
        goal: str | None,
        profile: UserProfile,
        *,
        user_key: str,
        session_id: str | None = None,
    ) -> HuntResult:
        original_goal = goal.strip() if goal else None
        resolved_goal, career_recommendation, used_recommendation = await self._resolve_goal(
            original_goal,
            profile,
        )
        strategy = await self.strategy_service.get_strategy(user_key)
        started_at = perf_counter()
        hunt = await self.repository.create_hunt(
            resolved_goal,
            user_key=user_key,
            original_goal=original_goal,
            career_recommendation=career_recommendation,
            goal_was_recommended=used_recommendation,
        )
        hunt_id = hunt.hunt_id
        session_id = session_id or hunt_id

        logger.info(
            "hunt_started",
            extra={
                "event": "hunt_started",
                "hunt_id": hunt_id,
                "user_key": user_key,
                "goal": resolved_goal,
                "original_goal": original_goal,
                "goal_was_recommended": used_recommendation,
                "behavior_type": strategy.behavior_type.value,
                "session_id": session_id,
            },
        )
        await self._publish(
            session_id,
            {
                "type": "hunt_started",
                "hunt_id": hunt_id,
                "user_key": user_key,
                "goal": resolved_goal,
                "goal_was_recommended": used_recommendation,
            },
        )

        try:
            plan = await self._run_step(
                hunt_id,
                StepType.PLAN,
                lambda: self._create_validated_plan(resolved_goal),
                lambda result, attempt, latency_ms: self.repository.save_plan(
                    hunt_id,
                    result,
                    attempt=attempt,
                    latency_ms=latency_ms,
                ),
            )

            jobs = await self._run_step(
                hunt_id,
                StepType.SEARCH,
                lambda: self._search_jobs(
                    plan,
                    resolved_goal,
                    hunt_id,
                    strategy,
                    profile,
                    user_key=user_key,
                    session_id=session_id,
                ),
                lambda result, attempt, latency_ms: self.repository.replace_jobs(
                    hunt_id,
                    result,
                    attempt=attempt,
                    latency_ms=latency_ms,
                ),
            )

            applications = await self._run_step(
                hunt_id,
                StepType.APPLY,
                lambda: self._prepare_applications(hunt_id, jobs, strategy),
                lambda result, attempt, latency_ms: self.repository.replace_applications(
                    hunt_id,
                    result,
                    user_key=user_key,
                    fingerprints_by_application_id=(
                        self.resume_correlation_service.fingerprint_application_batch(
                            user_id=user_key,
                            applications=result,
                        )
                    ),
                    attempt=attempt,
                    latency_ms=latency_ms,
                ),
            )
            await self.resume_correlation_service.refresh_profile(user_key)
            await self.tracking_service.refresh_behavior_snapshot(user_key)

            await self._run_step(
                hunt_id,
                StepType.TRACK,
                lambda: self.agents.tracker.build_entries(hunt_id, applications),
                lambda _result, attempt, latency_ms: self.repository.complete_tracking_step(
                    hunt_id,
                    attempt=attempt,
                    latency_ms=latency_ms,
                ),
            )

            await self.repository.mark_hunt_completed(hunt_id)
            result = await self.repository.get_hunt_result(hunt_id)

            logger.info(
                "hunt_completed",
                extra={
                    "event": "hunt_completed",
                    "hunt_id": hunt_id,
                    "user_key": user_key,
                    "latency_ms": self._latency_ms(started_at),
                    "jobs": len(result.jobs_found),
                    "applications": len(result.applications),
                    "behavior_type": strategy.behavior_type.value,
                },
            )
            await self._publish(
                session_id,
                {
                    "type": "hunt_completed",
                    "hunt_id": hunt_id,
                    "jobs": len(result.jobs_found),
                    "applications": len(result.applications),
                    "latency_ms": self._latency_ms(started_at),
                },
            )
            return result

        except ServiceError as exc:
            exc.errors = self._attach_hunt_id(exc.errors, hunt_id)
            await self.repository.mark_hunt_failed(hunt_id, exc.errors)
            logger.error(
                "hunt_failed",
                extra={
                    "event": "hunt_failed",
                    "hunt_id": hunt_id,
                    "latency_ms": self._latency_ms(started_at),
                    "errors": [error.model_dump(mode="json") for error in exc.errors],
                },
            )
            await self._publish(
                session_id,
                {
                    "type": "hunt_failed",
                    "hunt_id": hunt_id,
                    "errors": [error.model_dump(mode="json") for error in exc.errors],
                },
            )
            raise
        except Exception as exc:
            error = ErrorDetail(
                code="internal_orchestration_error",
                message="Unhandled orchestration failure",
                hunt_id=hunt_id,
                step="hunt",
                details={"reason": str(exc)},
            )
            await self.repository.mark_hunt_failed(hunt_id, [error])
            logger.exception(
                "hunt_failed_unhandled",
                extra={
                    "event": "hunt_failed_unhandled",
                    "hunt_id": hunt_id,
                    "latency_ms": self._latency_ms(started_at),
                },
            )
            await self._publish(
                session_id,
                {
                    "type": "hunt_failed",
                    "hunt_id": hunt_id,
                    "errors": [error.model_dump(mode="json")],
                },
            )
            raise PipelineExecutionError("Hunt execution failed", errors=[error]) from exc

    async def recommend_career(self, profile: UserProfile) -> CareerRecommendation:
        return await self.agents.career_advisor.recommend(profile)

    async def _run_step(
        self,
        hunt_id: str,
        step_type: StepType,
        operation: Callable[[], Awaitable[T]],
        persist: Callable[[T, int, int], Awaitable[None]],
    ) -> T:
        attempt = 0
        while True:
            attempt += 1
            started_at = perf_counter()
            await self.repository.mark_step_started(hunt_id, step_type, attempt=attempt)
            logger.info(
                "step_started",
                extra={
                    "event": "step_started",
                    "hunt_id": hunt_id,
                    "step": step_type.value,
                    "attempt": attempt,
                },
            )
            await self._publish(
                hunt_id,
                {
                    "type": "step_started",
                    "hunt_id": hunt_id,
                    "step": step_type.value,
                    "attempt": attempt,
                },
            )
            try:
                result = await asyncio.wait_for(
                    operation(),
                    timeout=STEP_TIMEOUT_SECONDS,
                )
                latency_ms = self._latency_ms(started_at)
                await persist(result, attempt, latency_ms)
                logger.info(
                    "step_completed",
                    extra={
                        "event": "step_completed",
                        "hunt_id": hunt_id,
                        "step": step_type.value,
                        "attempt": attempt,
                        "latency_ms": latency_ms,
                    },
                )
                await self._publish(
                    hunt_id,
                    {
                        "type": "step_completed",
                        "hunt_id": hunt_id,
                        "step": step_type.value,
                        "attempt": attempt,
                        "latency_ms": latency_ms,
                    },
                )
                return result
            except PlanValidationError as exc:
                errors = self._attach_hunt_id(exc.errors, hunt_id, step_type.value)
                await self.repository.mark_step_failed(
                    hunt_id,
                    step_type,
                    errors,
                    attempt=attempt,
                    latency_ms=self._latency_ms(started_at),
                )
                logger.error(
                    "step_failed",
                    extra={
                        "event": "step_failed",
                        "hunt_id": hunt_id,
                        "step": step_type.value,
                        "attempt": attempt,
                        "latency_ms": self._latency_ms(started_at),
                        "errors": [error.model_dump(mode="json") for error in errors],
                    },
                )
                await self._publish(
                    hunt_id,
                    {
                        "type": "step_failed",
                        "hunt_id": hunt_id,
                        "step": step_type.value,
                        "attempt": attempt,
                        "errors": [error.model_dump(mode="json") for error in errors],
                    },
                )
                await self._publish(
                    hunt_id,
                    {
                        "type": "FAILED",
                        "hunt_id": hunt_id,
                        "step": step_type.value,
                        "message": f"{self._display_step(step_type)} failed",
                        "errors": [error.model_dump(mode="json") for error in errors],
                    },
                )
                exc.errors = errors
                raise
            except asyncio.TimeoutError as exc:
                error = ErrorDetail(
                    code="step_timeout",
                    message=f"{self._display_step(step_type)} timed out",
                    hunt_id=hunt_id,
                    step=step_type.value,
                    retryable=True,
                    details={
                        "timeout_seconds": STEP_TIMEOUT_SECONDS,
                        "attempts": attempt,
                    },
                )
                if attempt < self.settings.step_retry_attempts:
                    await self.repository.mark_step_retryable_failure(
                        hunt_id,
                        step_type,
                        attempt=attempt,
                        errors=[error],
                        latency_ms=self._latency_ms(started_at),
                    )
                    delay_seconds = backoff_seconds(
                        attempt,
                        base_delay=self.settings.step_retry_base_delay_seconds,
                        max_delay=self.settings.step_retry_max_delay_seconds,
                    )
                    logger.warning(
                        "step_timeout_retrying",
                        extra={
                            "event": "step_timeout_retrying",
                            "hunt_id": hunt_id,
                            "step": step_type.value,
                            "attempt": attempt,
                            "latency_ms": self._latency_ms(started_at),
                            "retry_in_seconds": delay_seconds,
                            "timeout_seconds": STEP_TIMEOUT_SECONDS,
                        },
                    )
                    await self._publish(
                        hunt_id,
                        {
                            "type": "TIMEOUT",
                            "hunt_id": hunt_id,
                            "step": step_type.value,
                            "message": f"{self._display_step(step_type)} timed out",
                            "retry_in_seconds": delay_seconds,
                            "errors": [error.model_dump(mode="json")],
                        },
                    )
                    await asyncio.sleep(delay_seconds)
                    continue

                await self.repository.mark_step_failed(
                    hunt_id,
                    step_type,
                    [error],
                    attempt=attempt,
                    latency_ms=self._latency_ms(started_at),
                )
                logger.error(
                    "step_timeout",
                    extra={
                        "event": "step_timeout",
                        "hunt_id": hunt_id,
                        "step": step_type.value,
                        "attempt": attempt,
                        "latency_ms": self._latency_ms(started_at),
                        "errors": [error.model_dump(mode="json")],
                    },
                )
                await self._publish(
                    hunt_id,
                    {
                        "type": "TIMEOUT",
                        "hunt_id": hunt_id,
                        "step": step_type.value,
                        "message": f"{self._display_step(step_type)} timed out",
                        "errors": [error.model_dump(mode="json")],
                    },
                )
                raise StepExecutionError(
                    f"Step '{step_type.value}' timed out",
                    errors=[error],
                ) from exc
            except ServiceError as exc:
                errors = self._attach_hunt_id(exc.errors, hunt_id, step_type.value)
                exc.errors = errors
                if attempt < self.settings.step_retry_attempts and is_transient_error(exc):
                    await self.repository.mark_step_retryable_failure(
                        hunt_id,
                        step_type,
                        attempt=attempt,
                        errors=errors,
                        latency_ms=self._latency_ms(started_at),
                    )
                    delay_seconds = backoff_seconds(
                        attempt,
                        base_delay=self.settings.step_retry_base_delay_seconds,
                        max_delay=self.settings.step_retry_max_delay_seconds,
                    )
                    logger.warning(
                        "step_retrying",
                        extra={
                            "event": "step_retrying",
                            "hunt_id": hunt_id,
                            "step": step_type.value,
                            "attempt": attempt,
                            "latency_ms": self._latency_ms(started_at),
                            "retry_in_seconds": delay_seconds,
                            "errors": [error.model_dump(mode="json") for error in errors],
                        },
                    )
                    await self._publish(
                        hunt_id,
                        {
                            "type": "step_retrying",
                            "hunt_id": hunt_id,
                            "step": step_type.value,
                            "attempt": attempt,
                            "retry_in_seconds": delay_seconds,
                            "errors": [error.model_dump(mode="json") for error in errors],
                        },
                    )
                    await asyncio.sleep(delay_seconds)
                    continue

                await self.repository.mark_step_failed(
                    hunt_id,
                    step_type,
                    errors,
                    attempt=attempt,
                    latency_ms=self._latency_ms(started_at),
                )
                logger.error(
                    "step_failed",
                    extra={
                        "event": "step_failed",
                        "hunt_id": hunt_id,
                        "step": step_type.value,
                        "attempt": attempt,
                        "latency_ms": self._latency_ms(started_at),
                        "errors": [error.model_dump(mode="json") for error in errors],
                    },
                )
                await self._publish(
                    hunt_id,
                    {
                        "type": "step_failed",
                        "hunt_id": hunt_id,
                        "step": step_type.value,
                        "attempt": attempt,
                        "errors": [error.model_dump(mode="json") for error in errors],
                    },
                )
                await self._publish(
                    hunt_id,
                    {
                        "type": "FAILED",
                        "hunt_id": hunt_id,
                        "step": step_type.value,
                        "message": f"{self._display_step(step_type)} failed",
                        "errors": [error.model_dump(mode="json") for error in errors],
                    },
                )
                raise
            except Exception as exc:
                retryable = is_transient_error(exc)
                error = ErrorDetail(
                    code="step_execution_failed",
                    message=f"Step '{step_type.value}' failed",
                    hunt_id=hunt_id,
                    step=step_type.value,
                    retryable=retryable,
                    details={"reason": str(exc), "attempts": attempt},
                )
                if attempt < self.settings.step_retry_attempts and retryable:
                    await self.repository.mark_step_retryable_failure(
                        hunt_id,
                        step_type,
                        attempt=attempt,
                        errors=[error],
                        latency_ms=self._latency_ms(started_at),
                    )
                    delay_seconds = backoff_seconds(
                        attempt,
                        base_delay=self.settings.step_retry_base_delay_seconds,
                        max_delay=self.settings.step_retry_max_delay_seconds,
                    )
                    logger.warning(
                        "step_retrying",
                        extra={
                            "event": "step_retrying",
                            "hunt_id": hunt_id,
                            "step": step_type.value,
                            "attempt": attempt,
                            "latency_ms": self._latency_ms(started_at),
                            "retry_in_seconds": delay_seconds,
                            "reason": str(exc),
                        },
                    )
                    await self._publish(
                        hunt_id,
                        {
                            "type": "step_retrying",
                            "hunt_id": hunt_id,
                            "step": step_type.value,
                            "attempt": attempt,
                            "retry_in_seconds": delay_seconds,
                            "reason": str(exc),
                        },
                    )
                    await asyncio.sleep(delay_seconds)
                    continue

                await self.repository.mark_step_failed(
                    hunt_id,
                    step_type,
                    [error],
                    attempt=attempt,
                    latency_ms=self._latency_ms(started_at),
                )
                logger.error(
                    "step_failed",
                    extra={
                        "event": "step_failed",
                        "hunt_id": hunt_id,
                        "step": step_type.value,
                        "attempt": attempt,
                        "latency_ms": self._latency_ms(started_at),
                        "errors": [error.model_dump(mode="json")],
                    },
                )
                await self._publish(
                    hunt_id,
                    {
                        "type": "step_failed",
                        "hunt_id": hunt_id,
                        "step": step_type.value,
                        "attempt": attempt,
                        "errors": [error.model_dump(mode="json")],
                    },
                )
                await self._publish(
                    hunt_id,
                    {
                        "type": "FAILED",
                        "hunt_id": hunt_id,
                        "step": step_type.value,
                        "message": f"{self._display_step(step_type)} failed",
                        "errors": [error.model_dump(mode="json")],
                    },
                )
                raise StepExecutionError(
                    f"Step '{step_type.value}' failed",
                    errors=[error],
                ) from exc

    async def _create_validated_plan(self, goal: str) -> ExecutionPlan:
        plan = await self.agents.planner.create_plan(goal)
        validate_execution_plan(plan)
        return plan

    async def _search_jobs(
        self,
        plan: ExecutionPlan,
        resolved_goal: str,
        hunt_id: str,
        strategy: StrategyAdjustment,
        profile: UserProfile,
        *,
        user_key: str,
        session_id: str,
    ) -> list[Job]:
        search_step = self._get_step(plan, StepType.SEARCH)
        logger.info(
            "DISCOVERY_STARTED",
            extra={
                "event": "discovery_started",
                "hunt_id": hunt_id,
                "query": search_step.parameters.get("query", resolved_goal),
                "user_key": user_key,
            },
        )
        search_result = await self.agents.job_finder.search(
            query=search_step.parameters.get("query", resolved_goal),
            location=search_step.parameters.get("location"),
            max_results=self.strategy_service.search_limit(
                search_step.parameters.get("max_results"),
                strategy,
            ),
        )
        logger.info(
            "DISCOVERY_SEARCH_COMPLETED",
            extra={
                "event": "discovery_search_completed",
                "hunt_id": hunt_id,
                "total_found": search_result.total_found,
            },
        )
        jobs = self._validate_search_result(search_result, hunt_id)
        selected_jobs = self.strategy_service.select_jobs(
            jobs,
            goal=resolved_goal,
            strategy=strategy,
        )
        if not selected_jobs:
            raise StepExecutionError(
                "Strategy filtering removed every job",
                errors=[
                    ErrorDetail(
                        code="no_jobs_after_strategy",
                        message="No jobs remained after adaptive strategy filtering",
                        hunt_id=hunt_id,
                        step=StepType.SEARCH.value,
                        details={
                            "behavior_type": strategy.behavior_type.value,
                            "min_fit_score": strategy.min_fit_score,
                        },
                    )
                ],
            )
        try:
            ranked_jobs = await asyncio.wait_for(
                self.abc_service.rank_jobs(
                    user_id=user_key,
                    hunt_id=hunt_id,
                    session_id=session_id,
                    goal=resolved_goal,
                    jobs=selected_jobs,
                    profile=profile,
                    filters={
                        "behavior_strategy": strategy.model_dump(mode="json"),
                        "role_similarity_required": strategy.role_similarity_required,
                        "min_fit_score": strategy.min_fit_score,
                        "max_applications": strategy.max_applications,
                    },
                ),
                timeout=30,
            )
        except asyncio.TimeoutError:
            logger.error(
                "RANKING_TIMEOUT",
                extra={"event": "ranking_timeout", "hunt_id": hunt_id},
            )
            ranked_jobs = [
                RankedJob(
                    job=job,
                    event_id="timeout-fallback",
                    job_id=job.job_id,
                    rank=idx,
                    job_category="general",
                    keyword_match=0.5,
                    skill_match=0.5,
                    education_match=0.5,
                    experience_match=0.5,
                    location_match=0.5,
                    base_match_score=0.5,
                    behavior_score=0.5,
                    outcome_score=0.5,
                    category_weight=0.5,
                    confidence=0.0,
                    confidence_percent=0.0,
                    uncertainty_percent=100.0,
                    evidence_strength=0.0,
                    exploration_bonus=0.0,
                    repetition_penalty=0.0,
                    final_score=0.5,
                    reason="Ranking timed out — showing unranked results",
                    explanation="ABC ranking service did not complete in time.",
                    signal_breakdown={},
                    strategy_weights={},
                    filters={},
                )
                for idx, job in enumerate(selected_jobs, start=1)
            ]
        logger.info(
            "DISCOVERY_RANKING_COMPLETED",
            extra={
                "event": "discovery_ranking_completed",
                "hunt_id": hunt_id,
                "jobs_ranked": len(ranked_jobs),
            },
        )
        logger.info(
            "strategy_applied",
            extra={
                "event": "strategy_applied",
                "hunt_id": hunt_id,
                "behavior_type": strategy.behavior_type.value,
                "strategy": strategy.model_dump(mode="json"),
                "jobs_before": len(jobs),
                "jobs_after": len(ranked_jobs),
                "abc_top_rank": ranked_jobs[0].model_dump(mode="json") if ranked_jobs else None,
            },
        )
        logger.info("DISCOVERY_COMPLETED", extra={"event": "discovery_completed", "hunt_id": hunt_id})
        return [ranked.job for ranked in ranked_jobs]

    async def _prepare_applications(
        self,
        hunt_id: str,
        jobs: list[Job],
        strategy: StrategyAdjustment,
    ) -> list[Application]:
        semaphore = asyncio.Semaphore(self.settings.max_parallel_job_tasks)
        resume_version = self.strategy_service.resume_version_for(strategy)

        async def build_application(job: Job) -> Application:
            async with semaphore:
                return await asyncio.wait_for(
                    self._build_single_application(
                        hunt_id,
                        job,
                        resume_version=resume_version,
                    ),
                    timeout=self.settings.request_timeout_seconds * 3,
                )

        results = await asyncio.gather(
            *(build_application(job) for job in jobs),
            return_exceptions=True,
        )

        applications: list[Application] = []
        errors: list[ErrorDetail] = []

        for job, result in zip(jobs, results, strict=False):
            if isinstance(result, Exception):
                if isinstance(result, ServiceError):
                    errors.extend(self._with_job_context(result.errors, job, hunt_id))
                else:
                    errors.append(
                        ErrorDetail(
                            code="application_preparation_failed",
                            message=f"Failed to prepare application for '{job.title}'",
                            hunt_id=hunt_id,
                            step=StepType.APPLY.value,
                            retryable=is_transient_error(result),
                            details={
                                "job_id": job.job_id,
                                "company": job.company,
                                "reason": str(result),
                            },
                        )
                    )
                continue
            applications.append(result)

        if errors:
            raise StepExecutionError("Apply step failed", errors=errors)

        return applications

    async def _build_single_application(
        self,
        hunt_id: str,
        job: Job,
        *,
        resume_version: str,
    ) -> Application:
        resume = await asyncio.wait_for(
            self.agents.resume_writer.generate(job),
            timeout=self.settings.llm_timeout_seconds,
        )
        cover_letter = await asyncio.wait_for(
            self.agents.cover_letter_writer.generate(job),
            timeout=self.settings.llm_timeout_seconds,
        )
        return await asyncio.wait_for(
            self.agents.application_builder.prepare(
                hunt_id,
                job,
                resume,
                cover_letter,
                resume_version=resume_version,
                is_referral=self.strategy_service.is_referral_candidate(job),
            ),
            timeout=self.settings.request_timeout_seconds,
        )

    @staticmethod
    def _display_step(step_type: StepType) -> str:
        labels = {
            StepType.PLAN: "Planner Agent",
            StepType.SEARCH: "Discovery Agent",
            StepType.APPLY: "Application Agent",
            StepType.TRACK: "Tracking Agent",
        }
        return labels.get(step_type, f"{step_type.value.title()} Agent")

    async def _resolve_goal(
        self,
        goal: str | None,
        profile: UserProfile,
    ) -> tuple[str, CareerRecommendation | None, bool]:
        if goal and not self._is_vague_goal(goal):
            return goal, None, False

        if not profile.has_signal():
            raise BadRequestError(
                "A clear goal or a usable profile is required to start a hunt",
                errors=[
                    ErrorDetail(
                        code="missing_goal_or_profile",
                        message="Provide a specific goal or enough profile information for career recommendations",
                        step="career_recommendation",
                    )
                ],
            )

        recommendation = await self.recommend_career(profile)
        top_role = recommendation.recommended_roles[0].role
        logger.info(
            "goal_refined_from_profile",
            extra={
                "event": "goal_refined_from_profile",
                "original_goal": goal,
                "refined_goal": top_role,
            },
        )
        return top_role, recommendation, True

    @staticmethod
    def _get_step(plan: ExecutionPlan, step_type: StepType):
        for step in plan.steps:
            if step.step_type == step_type:
                return step
        raise PlanValidationError(
            f"Plan is missing required step '{step_type.value}'",
            errors=[
                ErrorDetail(
                    code="missing_plan_step",
                    message=f"Planner omitted required step '{step_type.value}'",
                    step=StepType.PLAN.value,
                    details={"expected_step": step_type.value},
                )
            ],
        )

    @staticmethod
    def _validate_search_result(search_result: JobSearchResult, hunt_id: str) -> list[Job]:
        if not search_result.jobs:
            raise StepExecutionError(
                "Search returned no jobs",
                errors=[
                    ErrorDetail(
                        code="no_jobs_found",
                        message="Search step completed without any jobs to process",
                        hunt_id=hunt_id,
                        step=StepType.SEARCH.value,
                    )
                ],
            )
        return [job.model_copy(update={"hunt_id": hunt_id}) for job in search_result.jobs]

    @staticmethod
    def _with_job_context(
        errors: list[ErrorDetail],
        job: Job,
        hunt_id: str,
    ) -> list[ErrorDetail]:
        return [
            error.model_copy(
                update={
                    "hunt_id": error.hunt_id or hunt_id,
                    "step": error.step or StepType.APPLY.value,
                    "details": {
                        **error.details,
                        "job_id": job.job_id,
                        "job_title": job.title,
                        "company": job.company,
                    },
                }
            )
            for error in errors
        ]

    @staticmethod
    def _attach_hunt_id(
        errors: list[ErrorDetail],
        hunt_id: str,
        default_step: str | None = None,
    ) -> list[ErrorDetail]:
        return [
            error.model_copy(
                update={
                    "hunt_id": error.hunt_id or hunt_id,
                    "step": error.step or default_step,
                }
            )
            for error in errors
        ]

    @staticmethod
    def _latency_ms(started_at: float) -> int:
        return round((perf_counter() - started_at) * 1000)

    async def _publish(self, channel: str, payload: dict) -> None:
        if self.event_bus is None:
            return
        await self.event_bus.publish(channel, payload)

    @staticmethod
    def _is_vague_goal(goal: str) -> bool:
        normalized_goal = goal.strip().lower()
        vague_phrases = {
            "",
            "anything",
            "any job",
            "help me decide",
            "i don't know",
            "idk",
            "not sure",
            "something good",
            "suggest something",
            "unsure",
            "whatever fits",
        }

        if normalized_goal in vague_phrases:
            return True

        role_keywords = (
            "engineer",
            "developer",
            "scientist",
            "analyst",
            "manager",
            "designer",
            "architect",
            "specialist",
            "consultant",
            "administrator",
        )
        return not any(keyword in normalized_goal for keyword in role_keywords)
