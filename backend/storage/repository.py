"""
Repository for all persisted hunt state.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.abc import (
    BehaviorEvent,
    BehaviorEventType,
    OutcomeEvent,
    OutcomeType,
    RecommendationEvent,
    UserStrategyProfile,
)
from backend.models.application import (
    Application,
    ApplicationStatus,
    CoverLetter,
    ResumeContent,
    TrackerEntry,
)
from backend.models.behavior import (
    ApplicationOutcomeStatus,
    BehaviorProfile,
)
from backend.models.career import CareerRecommendation
from backend.models.errors import ErrorDetail
from backend.models.hunt import HuntResult, HuntStatus, StepProgress, StepProgressStatus
from backend.models.intelligence import ConversationTurn, UserIntelligenceState
from backend.models.job import Job
from backend.models.plan import EXPECTED_STEP_ORDER, ExecutionPlan, PlanStep, StepType
from backend.models.resume_intelligence import (
    PredictiveCareerProfile,
    ResumeCorrelationProfile,
    ResumeFingerprint,
)
from backend.services.exceptions import NotFoundError, TooManyRequestsError
from backend.storage.records import (
    ApplicationRecord,
    BehaviorMetricSnapshotRecord,
    BehaviorEventRecord,
    ConversationTurnRecord,
    HuntRecord,
    JobRecord,
    OutcomeRecord,
    PredictiveCareerProfileRecord,
    PlanRecord,
    RateLimitRecord,
    RecommendationEventRecord,
    ResumeCorrelationProfileRecord,
    ResumeFingerprintRecord,
    StepExecutionRecord,
    UserStrategyProfileRecord,
    UserIntelligenceProfileRecord,
    utc_now,
)


class HuntRepository:
    """Persistence operations for hunts and their child entities."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_hunt(
        self,
        goal: str,
        *,
        user_key: str,
        original_goal: str | None = None,
        career_recommendation: CareerRecommendation | None = None,
        goal_was_recommended: bool = False,
    ) -> HuntRecord:
        now = utc_now()
        hunt_id = str(uuid.uuid4())
        record = HuntRecord(
            hunt_id=hunt_id,
            user_key=user_key,
            goal=goal,
            original_goal=original_goal,
            goal_was_recommended=goal_was_recommended,
            career_recommendation_json=(
                career_recommendation.model_dump(mode="json") if career_recommendation else None
            ),
            status=HuntStatus.RUNNING.value,
            error_count=0,
            errors=[],
            created_at=now,
            updated_at=now,
            completed_at=None,
        )
        step_records = [
            StepExecutionRecord(
                hunt_id=hunt_id,
                step_name=step_type.value,
                status=StepProgressStatus.PENDING.value,
                idempotency_key=self._build_idempotency_key(hunt_id, step_type),
                attempt_count=0,
                latency_ms=None,
                last_error_json=[],
                started_at=None,
                completed_at=None,
                updated_at=now,
            )
            for step_type in EXPECTED_STEP_ORDER
        ]

        async with self.session.begin():
            self.session.add(record)
            self.session.add_all(step_records)

        return record

    async def mark_step_started(
        self,
        hunt_id: str,
        step_type: StepType,
        *,
        attempt: int,
    ) -> None:
        async with self.session.begin():
            hunt = await self._get_hunt_record(hunt_id, for_update=True)
            step_record = await self._get_step_record(hunt_id, step_type, for_update=True)
            now = utc_now()
            step_record.status = StepProgressStatus.RUNNING.value
            step_record.attempt_count = attempt
            step_record.idempotency_key = self._build_idempotency_key(hunt_id, step_type)
            step_record.started_at = now
            step_record.completed_at = None
            step_record.latency_ms = None
            step_record.last_error_json = []
            step_record.updated_at = now
            hunt.updated_at = now

    async def mark_step_retryable_failure(
        self,
        hunt_id: str,
        step_type: StepType,
        *,
        attempt: int,
        errors: list[ErrorDetail],
        latency_ms: int,
    ) -> None:
        async with self.session.begin():
            hunt = await self._get_hunt_record(hunt_id, for_update=True)
            step_record = await self._get_step_record(hunt_id, step_type, for_update=True)
            now = utc_now()
            step_record.status = StepProgressStatus.RUNNING.value
            step_record.attempt_count = attempt
            step_record.latency_ms = latency_ms
            step_record.last_error_json = self._serialise_errors(errors)
            step_record.updated_at = now
            hunt.updated_at = now

    async def save_plan(
        self,
        hunt_id: str,
        plan: ExecutionPlan,
        *,
        attempt: int,
        latency_ms: int,
    ) -> None:
        async with self.session.begin():
            hunt = await self._get_hunt_record(hunt_id, for_update=True)
            step_record = await self._get_step_record(hunt_id, StepType.PLAN, for_update=True)
            await self.session.execute(delete(PlanRecord).where(PlanRecord.hunt_id == hunt_id))
            self.session.add(
                PlanRecord(
                    plan_id=str(uuid.uuid4()),
                    hunt_id=hunt_id,
                    summary=plan.summary,
                    step_count=len(plan.steps),
                    steps_json=plan.model_dump(mode="json")["steps"],
                )
            )
            hunt.goal = plan.goal
            self._mark_step_completed(step_record, attempt=attempt, latency_ms=latency_ms)
            hunt.updated_at = utc_now()

    async def replace_jobs(
        self,
        hunt_id: str,
        jobs: list[Job],
        *,
        attempt: int,
        latency_ms: int,
    ) -> None:
        unique_jobs = self._dedupe_jobs(jobs)

        async with self.session.begin():
            hunt = await self._get_hunt_record(hunt_id, for_update=True)
            step_record = await self._get_step_record(hunt_id, StepType.SEARCH, for_update=True)
            await self.session.execute(delete(JobRecord).where(JobRecord.hunt_id == hunt_id))
            self.session.add_all(
                [
                    JobRecord(
                        id=str(uuid.uuid4()),
                        hunt_id=hunt_id,
                        external_job_id=job.job_id,
                        title=job.title,
                        company=job.company,
                        location=job.location,
                        description=job.description,
                        requirements=job.requirements,
                        salary_range=job.salary_range,
                        url=job.url,
                        source=job.source,
                        posted_date=job.posted_date,
                        rank_position=job.ranking_position or index,
                        base_match_score=job.base_match_score,
                        final_score=job.final_score,
                        recommendation_reason=job.recommendation_reason,
                        recommendation_event_id=job.recommendation_event_id,
                        category=job.job_category,
                        scraped_at=job.scraped_at,
                    )
                    for index, job in enumerate(unique_jobs, start=1)
                ]
            )
            self._mark_step_completed(step_record, attempt=attempt, latency_ms=latency_ms)
            hunt.updated_at = utc_now()

    async def replace_applications(
        self,
        hunt_id: str,
        applications: list[Application],
        *,
        user_key: str,
        fingerprints_by_application_id: dict[str, ResumeFingerprint] | None = None,
        attempt: int,
        latency_ms: int,
    ) -> None:
        unique_applications = self._dedupe_applications(applications)
        fingerprints_by_application_id = fingerprints_by_application_id or {}

        async with self.session.begin():
            hunt = await self._get_hunt_record(hunt_id, for_update=True)
            step_record = await self._get_step_record(hunt_id, StepType.APPLY, for_update=True)
            await self.session.execute(
                delete(ApplicationRecord).where(ApplicationRecord.hunt_id == hunt_id)
            )
            for fingerprint in fingerprints_by_application_id.values():
                await self.session.merge(
                    ResumeFingerprintRecord(
                        id=fingerprint.fingerprint_id,
                        user_id=fingerprint.user_id,
                        resume_id=fingerprint.resume_id,
                        resume_version=fingerprint.resume_version,
                        content_hash=fingerprint.content_hash,
                        features_json=fingerprint.features.model_dump(mode="json"),
                        created_at=fingerprint.created_at,
                        updated_at=fingerprint.updated_at,
                    )
                )
            self.session.add_all(
                [
                    ApplicationRecord(
                        application_id=application.application_id,
                        user_key=user_key,
                        hunt_id=hunt_id,
                        job_id=application.job_id,
                        role=application.role,
                        job_title=application.job_title,
                        company=application.company,
                        platform=application.platform,
                        resume_version=application.resume_version,
                        resume_fingerprint_id=(
                            fingerprints_by_application_id[application.application_id].fingerprint_id
                            if application.application_id in fingerprints_by_application_id
                            else None
                        ),
                        timestamp_applied=application.timestamp_applied,
                        application_status=application.application_status.value,
                        is_referral=application.is_referral,
                        status=application.status.value,
                        resume_json=application.resume.model_dump(mode="json"),
                        cover_letter_json=application.cover_letter.model_dump(mode="json"),
                        notes=application.notes,
                        created_at=application.created_at,
                        submitted_at=application.submitted_at,
                    )
                    for application in unique_applications
                ]
            )
            self._mark_step_completed(step_record, attempt=attempt, latency_ms=latency_ms)
            hunt.updated_at = utc_now()

    async def complete_tracking_step(
        self,
        hunt_id: str,
        *,
        attempt: int,
        latency_ms: int,
    ) -> None:
        async with self.session.begin():
            hunt = await self._get_hunt_record(hunt_id, for_update=True)
            step_record = await self._get_step_record(hunt_id, StepType.TRACK, for_update=True)
            self._mark_step_completed(step_record, attempt=attempt, latency_ms=latency_ms)
            hunt.updated_at = utc_now()

    async def mark_step_failed(
        self,
        hunt_id: str,
        step_type: StepType,
        errors: list[ErrorDetail],
        *,
        attempt: int,
        latency_ms: int,
    ) -> None:
        async with self.session.begin():
            hunt = await self._get_hunt_record(hunt_id, for_update=True)
            step_record = await self._get_step_record(hunt_id, step_type, for_update=True)
            now = utc_now()
            step_record.status = StepProgressStatus.FAILED.value
            step_record.attempt_count = attempt
            step_record.latency_ms = latency_ms
            step_record.last_error_json = self._serialise_errors(errors)
            step_record.completed_at = now
            step_record.updated_at = now
            hunt.updated_at = now

    async def mark_hunt_completed(self, hunt_id: str) -> None:
        async with self.session.begin():
            hunt = await self._get_hunt_record(hunt_id, for_update=True)
            now = utc_now()
            hunt.status = HuntStatus.COMPLETED.value
            hunt.updated_at = now
            hunt.completed_at = now
            hunt.error_count = 0
            hunt.errors = []

    async def mark_hunt_failed(self, hunt_id: str, errors: list[ErrorDetail]) -> None:
        async with self.session.begin():
            hunt = await self._get_hunt_record(hunt_id, for_update=True)
            now = utc_now()
            hunt.status = HuntStatus.FAILED.value
            hunt.updated_at = now
            hunt.completed_at = now
            hunt.error_count = len(errors)
            hunt.errors = self._serialise_errors(errors)

    async def consume_rate_limit(
        self,
        *,
        client_key: str,
        route_key: str,
        max_requests: int,
        window_seconds: int,
    ) -> None:
        now = utc_now()
        bucket_start = self._floor_window(now, window_seconds)

        for attempt in range(2):
            try:
                async with self.session.begin():
                    statement = (
                        select(RateLimitRecord)
                        .where(RateLimitRecord.client_key == client_key)
                        .where(RateLimitRecord.route_key == route_key)
                        .where(RateLimitRecord.window_started_at == bucket_start)
                        .with_for_update()
                    )
                    record = await self.session.scalar(statement)
                    if record is None:
                        self.session.add(
                            RateLimitRecord(
                                client_key=client_key,
                                route_key=route_key,
                                window_started_at=bucket_start,
                                request_count=1,
                                updated_at=now,
                            )
                        )
                        return

                    if record.request_count >= max_requests:
                        retry_after_seconds = self._retry_after_seconds(
                            now,
                            bucket_start,
                            window_seconds,
                        )
                        raise TooManyRequestsError(
                            "Hunt rate limit exceeded",
                            errors=[
                                ErrorDetail(
                                    code="rate_limit_exceeded",
                                    message="Too many hunt requests for this client",
                                    step="hunt",
                                    details={
                                        "client_key": client_key,
                                        "limit": max_requests,
                                        "window_seconds": window_seconds,
                                        "retry_after_seconds": retry_after_seconds,
                                    },
                                )
                            ],
                        )

                    record.request_count += 1
                    record.updated_at = now
                    return
            except IntegrityError:
                await self.session.rollback()
                if attempt == 1:
                    raise

    async def get_hunt_result(self, hunt_id: str) -> HuntResult:
        hunt = await self._get_hunt_record(hunt_id)

        plan_record = await self.session.scalar(
            select(PlanRecord).where(PlanRecord.hunt_id == hunt_id)
        )
        job_records = (
            await self.session.scalars(
                select(JobRecord)
                .where(JobRecord.hunt_id == hunt_id)
                .order_by(JobRecord.rank_position, JobRecord.title)
            )
        ).all()
        application_records = (
            await self.session.scalars(
                select(ApplicationRecord)
                .where(ApplicationRecord.hunt_id == hunt_id)
                .order_by(ApplicationRecord.created_at)
            )
        ).all()
        step_records = (
            await self.session.scalars(
                select(StepExecutionRecord)
                .where(StepExecutionRecord.hunt_id == hunt_id)
                .order_by(StepExecutionRecord.id)
            )
        ).all()

        plan = (
            ExecutionPlan(
                goal=hunt.goal,
                summary=plan_record.summary,
                steps=[PlanStep(**step) for step in plan_record.steps_json],
            )
            if plan_record
            else None
        )

        jobs = [
            Job(
                hunt_id=hunt_id,
                job_id=record.external_job_id,
                title=record.title,
                company=record.company,
                location=record.location,
                description=record.description,
                requirements=record.requirements,
                salary_range=record.salary_range,
                url=record.url,
                source=record.source,
                posted_date=record.posted_date,
                scraped_at=record.scraped_at,
                ranking_position=record.rank_position,
                base_match_score=record.base_match_score,
                final_score=record.final_score,
                recommendation_reason=record.recommendation_reason,
                recommendation_event_id=record.recommendation_event_id,
                job_category=record.category,
            )
            for record in job_records
        ]

        applications = [
            Application(
                hunt_id=hunt_id,
                application_id=record.application_id,
                job_id=record.job_id,
                role=record.role or record.job_title,
                job_title=record.job_title,
                company=record.company,
                platform=record.platform,
                resume_version=record.resume_version,
                timestamp_applied=record.timestamp_applied,
                application_status=ApplicationOutcomeStatus(record.application_status),
                is_referral=record.is_referral,
                resume=ResumeContent(**record.resume_json),
                cover_letter=CoverLetter(**record.cover_letter_json),
                status=ApplicationStatus(record.status),
                created_at=record.created_at,
                submitted_at=record.submitted_at,
                notes=record.notes,
            )
            for record in application_records
        ]

        tracker = [
            TrackerEntry(
                hunt_id=hunt_id,
                application_id=application.application_id,
                job_id=application.job_id,
                job_title=application.job_title,
                company=application.company,
                platform=application.platform,
                resume_version=application.resume_version,
                application_status=application.application_status,
                is_referral=application.is_referral,
                status=application.status,
                created_at=application.created_at,
                submitted_at=application.submitted_at,
            )
            for application in applications
        ]

        progress = self._build_progress(hunt_id, step_records)
        progress_counts = self._count_progress(progress)
        errors = self._deserialise_errors(hunt.errors)

        return HuntResult(
            hunt_id=hunt.hunt_id,
            goal=hunt.goal,
            original_goal=hunt.original_goal,
            career_recommendation=(
                CareerRecommendation(**hunt.career_recommendation_json)
                if hunt.career_recommendation_json
                else None
            ),
            goal_was_recommended=hunt.goal_was_recommended,
            status=HuntStatus(hunt.status),
            plan=plan,
            jobs_found=jobs,
            applications=applications,
            tracker=tracker,
            progress=progress,
            errors=errors,
            created_at=hunt.created_at,
            completed_at=hunt.completed_at,
            summary={
                "total_jobs": len(jobs),
                "total_applications": len(applications),
                "tracked_applications": len(tracker),
                "error_count": hunt.error_count,
                **progress_counts,
            },
        )

    async def get_jobs_for_hunt(self, hunt_id: str) -> list[Job]:
        result = await self.get_hunt_result(hunt_id)
        return result.jobs_found

    async def get_applications_for_hunt(self, hunt_id: str) -> list[Application]:
        result = await self.get_hunt_result(hunt_id)
        return result.applications

    async def list_application_records(
        self,
        user_key: str,
        *,
        window_days: int,
    ) -> list[ApplicationRecord]:
        since = utc_now() - timedelta(days=window_days)
        statement = (
            select(ApplicationRecord)
            .where(ApplicationRecord.user_key == user_key)
            .where(ApplicationRecord.timestamp_applied >= since)
            .order_by(ApplicationRecord.timestamp_applied)
        )
        records = list((await self.session.scalars(statement)).all())
        if self.session.in_transaction():
            await self.session.commit()
        return records

    async def list_all_application_records(self, user_key: str) -> list[ApplicationRecord]:
        records = list(
            (
                await self.session.scalars(
                    select(ApplicationRecord)
                    .where(ApplicationRecord.user_key == user_key)
                    .order_by(ApplicationRecord.timestamp_applied)
                )
            ).all()
        )
        if self.session.in_transaction():
            await self.session.commit()
        return records

    async def save_behavior_snapshot(self, profile: BehaviorProfile) -> None:
        metrics = profile.metrics
        async with self.session.begin():
            self.session.add(
                BehaviorMetricSnapshotRecord(
                    user_key=profile.user_key,
                    classification=profile.classification.value,
                    total_applications=metrics.total_applications,
                    analysis_window_days=metrics.analysis_window_days,
                    observed_days=metrics.observed_days,
                    apps_per_day=metrics.apps_per_day,
                    success_rate=metrics.success_rate,
                    platform_distribution=metrics.platform_distribution,
                    role_distribution=metrics.role_distribution,
                    role_diversity=metrics.role_diversity,
                    resume_success_rate=metrics.resume_success_rate,
                    referral_ratio=metrics.referral_ratio,
                    minimum_data_threshold_met=metrics.minimum_data_threshold_met,
                    created_at=profile.updated_at,
                )
            )

    async def save_recommendation_events(
        self,
        events: list[RecommendationEvent],
    ) -> None:
        if not events:
            return

        async with self.session.begin():
            self.session.add_all(
                [
                    RecommendationEventRecord(
                        id=event.event_id,
                        event_type=event.event_type,
                        user_id=event.user_id,
                        hunt_id=event.hunt_id,
                        session_id=event.session_id,
                        job_id=event.job_id,
                        category=event.job_category,
                        rank_position=event.ranking_position,
                        base_match_score=event.base_match_score,
                        final_score=event.final_score,
                        recommendation_reason=event.recommendation_reason,
                        strategy_snapshot_json=event.strategy_weights_used,
                        filters_json=event.filters_applied,
                        created_at=event.timestamp,
                    )
                    for event in events
                ]
            )

    async def get_recommendation_event_record(
        self,
        event_id: str,
    ) -> RecommendationEventRecord:
        record = await self.session.scalar(
            select(RecommendationEventRecord).where(RecommendationEventRecord.id == event_id)
        )
        if self.session.in_transaction():
            await self.session.commit()
        if record is None:
            raise NotFoundError(
                f"Recommendation event '{event_id}' was not found",
                errors=[
                    ErrorDetail(
                        code="recommendation_event_not_found",
                        message="Recommendation context does not exist",
                        details={"event_id": event_id},
                    )
                ],
            )
        return record

    async def save_behavior_event(self, event: BehaviorEvent) -> None:
        async with self.session.begin():
            self.session.add(
                BehaviorEventRecord(
                    id=event.event_id,
                    antecedent_event_id=event.antecedent_event_id,
                    user_id=event.user_id,
                    hunt_id=event.hunt_id,
                    session_id=event.session_id,
                    event_type=event.event_type.value,
                    job_id=event.job_id,
                    resume_id=event.resume_id,
                    category=event.job_category,
                    created_at=event.timestamp,
                )
            )

    async def get_behavior_event_record(self, event_id: str) -> BehaviorEventRecord:
        record = await self.session.scalar(
            select(BehaviorEventRecord).where(BehaviorEventRecord.id == event_id)
        )
        if self.session.in_transaction():
            await self.session.commit()
        if record is None:
            raise NotFoundError(
                f"Behavior event '{event_id}' was not found",
                errors=[
                    ErrorDetail(
                        code="behavior_event_not_found",
                        message="Behavior event does not exist",
                        details={"event_id": event_id},
                    )
                ],
            )
        return record

    async def save_outcome_event(self, event: OutcomeEvent) -> None:
        async with self.session.begin():
            self.session.add(
                OutcomeRecord(
                    id=event.outcome_id,
                    behavior_event_id=event.behavior_event_id,
                    outcome_type=event.outcome_type.value,
                    response_time_days=event.response_time_days,
                    created_at=event.timestamp,
                )
            )

    async def list_abc_records(
        self,
        user_id: str,
    ) -> tuple[
        list[RecommendationEventRecord],
        list[BehaviorEventRecord],
        list[OutcomeRecord],
    ]:
        recommendation_records = list(
            (
                await self.session.scalars(
                    select(RecommendationEventRecord)
                    .where(RecommendationEventRecord.user_id == user_id)
                    .order_by(RecommendationEventRecord.created_at)
                )
            ).all()
        )
        behavior_records = list(
            (
                await self.session.scalars(
                    select(BehaviorEventRecord)
                    .where(BehaviorEventRecord.user_id == user_id)
                    .order_by(BehaviorEventRecord.created_at)
                )
            ).all()
        )
        outcome_records = list(
            (
                await self.session.scalars(
                    select(OutcomeRecord)
                    .join(
                        BehaviorEventRecord,
                        OutcomeRecord.behavior_event_id == BehaviorEventRecord.id,
                    )
                    .where(BehaviorEventRecord.user_id == user_id)
                    .order_by(OutcomeRecord.created_at)
                )
            ).all()
        )
        if self.session.in_transaction():
            await self.session.commit()
        return recommendation_records, behavior_records, outcome_records

    async def get_user_strategy_profile(
        self,
        user_id: str,
    ) -> UserStrategyProfile | None:
        record = await self.session.scalar(
            select(UserStrategyProfileRecord).where(UserStrategyProfileRecord.user_id == user_id)
        )
        if self.session.in_transaction():
            await self.session.commit()
        if record is None:
            return None
        return UserStrategyProfile(
            user_id=record.user_id,
            category_weights=record.category_weights_json,
            category_success_rates=record.category_success_rates_json,
            click_rates=record.click_rates_json,
            application_rates=record.application_rates_json,
            avg_response_times=record.avg_response_times_json,
            category_profiles=record.category_profiles_json,
            updated_at=record.updated_at,
        )

    async def upsert_user_strategy_profile(self, profile: UserStrategyProfile) -> None:
        async with self.session.begin():
            await self.session.merge(
                UserStrategyProfileRecord(
                    user_id=profile.user_id,
                    category_weights_json=profile.category_weights,
                    category_success_rates_json=profile.category_success_rates,
                    click_rates_json=profile.click_rates,
                    application_rates_json=profile.application_rates,
                    avg_response_times_json=profile.avg_response_times,
                    category_profiles_json={
                        key: value.model_dump(mode="json")
                        for key, value in profile.category_profiles.items()
                    },
                    updated_at=profile.updated_at,
                )
            )

    async def save_conversation_turn(self, turn: ConversationTurn) -> None:
        async with self.session.begin():
            self.session.add(
                ConversationTurnRecord(
                    id=turn.turn_id,
                    user_id=turn.user_id,
                    session_id=turn.session_id,
                    message=turn.message,
                    extracted_signals_json=turn.extracted_signals,
                    category_preferences_json=turn.category_preferences,
                    created_at=turn.created_at,
                )
            )

    async def list_conversation_turns(
        self,
        user_id: str,
        *,
        limit: int = 50,
    ) -> list[ConversationTurn]:
        records = list(
            (
                await self.session.scalars(
                    select(ConversationTurnRecord)
                    .where(ConversationTurnRecord.user_id == user_id)
                    .order_by(ConversationTurnRecord.created_at.desc())
                    .limit(limit)
                )
            ).all()
        )
        if self.session.in_transaction():
            await self.session.commit()
        return [
            ConversationTurn(
                turn_id=record.id,
                user_id=record.user_id,
                session_id=record.session_id,
                message=record.message,
                extracted_signals=record.extracted_signals_json,
                category_preferences=record.category_preferences_json,
                created_at=record.created_at,
            )
            for record in reversed(records)
        ]

    async def get_user_intelligence_profile(
        self,
        user_id: str,
    ) -> UserIntelligenceState | None:
        record = await self.session.scalar(
            select(UserIntelligenceProfileRecord).where(
                UserIntelligenceProfileRecord.user_id == user_id
            )
        )
        if self.session.in_transaction():
            await self.session.commit()
        if record is None:
            return None
        return UserIntelligenceState(
            user_id=record.user_id,
            intent=record.latest_intent_json,
            discovery=record.latest_discovery_json,
            confidence=record.latest_confidence_json,
            conversation_count=record.conversation_count,
            updated_at=record.updated_at,
        )

    async def upsert_user_intelligence_profile(self, state: UserIntelligenceState) -> None:
        async with self.session.begin():
            await self.session.merge(
                UserIntelligenceProfileRecord(
                    user_id=state.user_id,
                    latest_intent_json=state.intent.model_dump(mode="json"),
                    latest_discovery_json=state.discovery.model_dump(mode="json"),
                    latest_confidence_json=state.confidence.model_dump(mode="json"),
                    conversation_count=state.conversation_count,
                    updated_at=state.updated_at,
                )
            )

    async def recent_recommendation_history(
        self,
        user_id: str,
        job_ids: list[str],
    ) -> dict[str, tuple[float, int]]:
        if not job_ids:
            return {}
        records = list(
            (
                await self.session.scalars(
                    select(RecommendationEventRecord)
                    .where(RecommendationEventRecord.user_id == user_id)
                    .where(RecommendationEventRecord.job_id.in_(job_ids))
                    .order_by(
                        RecommendationEventRecord.job_id,
                        RecommendationEventRecord.created_at.desc(),
                    )
                )
            ).all()
        )
        if self.session.in_transaction():
            await self.session.commit()

        history: dict[str, tuple[float, int]] = {}
        for record in records:
            previous_score, count = history.get(record.job_id, (record.final_score, 0))
            latest_score = previous_score if count else record.final_score
            history[record.job_id] = (latest_score, count + 1)
        return history

    async def upsert_resume_fingerprint(self, fingerprint: ResumeFingerprint) -> None:
        async with self.session.begin():
            await self.session.merge(
                ResumeFingerprintRecord(
                    id=fingerprint.fingerprint_id,
                    user_id=fingerprint.user_id,
                    resume_id=fingerprint.resume_id,
                    resume_version=fingerprint.resume_version,
                    content_hash=fingerprint.content_hash,
                    features_json=fingerprint.features.model_dump(mode="json"),
                    created_at=fingerprint.created_at,
                    updated_at=fingerprint.updated_at,
                )
            )

    async def get_resume_fingerprint(
        self,
        user_id: str,
        resume_id: str,
    ) -> ResumeFingerprint | None:
        record = await self.session.scalar(
            select(ResumeFingerprintRecord)
            .where(ResumeFingerprintRecord.user_id == user_id)
            .where(ResumeFingerprintRecord.resume_id == resume_id)
            .order_by(ResumeFingerprintRecord.updated_at.desc())
        )
        if self.session.in_transaction():
            await self.session.commit()
        if record is None:
            return None
        return self._resume_fingerprint_from_record(record)

    async def list_resume_fingerprints(self, user_id: str) -> list[ResumeFingerprint]:
        records = list(
            (
                await self.session.scalars(
                    select(ResumeFingerprintRecord)
                    .where(ResumeFingerprintRecord.user_id == user_id)
                    .order_by(ResumeFingerprintRecord.updated_at)
                )
            ).all()
        )
        if self.session.in_transaction():
            await self.session.commit()
        return [self._resume_fingerprint_from_record(record) for record in records]

    async def get_resume_fingerprint_records_by_ids(
        self,
        fingerprint_ids: list[str],
    ) -> dict[str, ResumeFingerprint]:
        if not fingerprint_ids:
            return {}
        records = list(
            (
                await self.session.scalars(
                    select(ResumeFingerprintRecord).where(
                        ResumeFingerprintRecord.id.in_(fingerprint_ids)
                    )
                )
            ).all()
        )
        if self.session.in_transaction():
            await self.session.commit()
        return {
            record.id: self._resume_fingerprint_from_record(record)
            for record in records
        }

    async def get_resume_correlation_profile(
        self,
        user_id: str,
    ) -> ResumeCorrelationProfile | None:
        record = await self.session.scalar(
            select(ResumeCorrelationProfileRecord).where(
                ResumeCorrelationProfileRecord.user_id == user_id
            )
        )
        if self.session.in_transaction():
            await self.session.commit()
        if record is None:
            return None
        return ResumeCorrelationProfile(
            user_id=record.user_id,
            feature_correlations=record.feature_correlations_json,
            resume_effectiveness=record.resume_effectiveness_json,
            total_linked_outcomes=record.total_linked_outcomes,
            updated_at=record.updated_at,
        )

    async def upsert_resume_correlation_profile(
        self,
        profile: ResumeCorrelationProfile,
    ) -> None:
        async with self.session.begin():
            await self.session.merge(
                ResumeCorrelationProfileRecord(
                    user_id=profile.user_id,
                    feature_correlations_json={
                        key: value.model_dump(mode="json")
                        for key, value in profile.feature_correlations.items()
                    },
                    resume_effectiveness_json={
                        key: value.model_dump(mode="json")
                        for key, value in profile.resume_effectiveness.items()
                    },
                    total_linked_outcomes=profile.total_linked_outcomes,
                    updated_at=profile.updated_at,
                )
            )

    async def get_predictive_career_profile(
        self,
        user_id: str,
    ) -> PredictiveCareerProfile | None:
        record = await self.session.scalar(
            select(PredictiveCareerProfileRecord).where(
                PredictiveCareerProfileRecord.user_id == user_id
            )
        )
        if self.session.in_transaction():
            await self.session.commit()
        if record is None:
            return None
        return PredictiveCareerProfile(
            user_id=record.user_id,
            user_vector=record.user_vector_json,
            predictions=record.predictions_json,
            updated_at=record.updated_at,
        )

    async def upsert_predictive_career_profile(
        self,
        profile: PredictiveCareerProfile,
    ) -> None:
        async with self.session.begin():
            await self.session.merge(
                PredictiveCareerProfileRecord(
                    user_id=profile.user_id,
                    user_vector_json=profile.user_vector.model_dump(mode="json"),
                    predictions_json=[
                        prediction.model_dump(mode="json")
                        for prediction in profile.predictions
                    ],
                    updated_at=profile.updated_at,
                )
            )

    async def _get_hunt_record(self, hunt_id: str, *, for_update: bool = False) -> HuntRecord:
        statement = select(HuntRecord).where(HuntRecord.hunt_id == hunt_id)
        if for_update:
            statement = statement.with_for_update()
        hunt = await self.session.scalar(statement)
        if hunt is None:
            raise NotFoundError(
                f"Hunt '{hunt_id}' was not found",
                errors=[
                    ErrorDetail(
                        code="hunt_not_found",
                        message=f"Hunt '{hunt_id}' does not exist",
                        hunt_id=hunt_id,
                    )
                ],
            )
        return hunt

    async def _get_step_record(
        self,
        hunt_id: str,
        step_type: StepType,
        *,
        for_update: bool = False,
    ) -> StepExecutionRecord:
        statement = (
            select(StepExecutionRecord)
            .where(StepExecutionRecord.hunt_id == hunt_id)
            .where(StepExecutionRecord.step_name == step_type.value)
        )
        if for_update:
            statement = statement.with_for_update()
        step_record = await self.session.scalar(statement)
        if step_record is None:
            raise NotFoundError(
                f"Step '{step_type.value}' for hunt '{hunt_id}' was not found",
                errors=[
                    ErrorDetail(
                        code="step_not_found",
                        message=f"Step '{step_type.value}' does not exist for this hunt",
                        hunt_id=hunt_id,
                        step=step_type.value,
                    )
                ],
            )
        return step_record

    @staticmethod
    def _build_idempotency_key(hunt_id: str, step_type: StepType) -> str:
        return f"{hunt_id}:{step_type.value}:v1"

    @staticmethod
    def _mark_step_completed(
        step_record: StepExecutionRecord,
        *,
        attempt: int,
        latency_ms: int,
    ) -> None:
        now = utc_now()
        step_record.status = StepProgressStatus.COMPLETED.value
        step_record.attempt_count = attempt
        step_record.latency_ms = latency_ms
        step_record.last_error_json = []
        step_record.completed_at = now
        step_record.updated_at = now

    @staticmethod
    def _serialise_errors(errors: list[ErrorDetail]) -> list[dict[str, object]]:
        return [error.model_dump(mode="json") for error in errors]

    @staticmethod
    def _deserialise_errors(payload: list[dict[str, object]]) -> list[ErrorDetail]:
        return [ErrorDetail(**error) for error in payload]

    @staticmethod
    def _dedupe_jobs(jobs: list[Job]) -> list[Job]:
        unique: dict[str, Job] = {}
        for job in jobs:
            unique.setdefault(job.job_id, job)
        return list(unique.values())

    @staticmethod
    def _dedupe_applications(applications: list[Application]) -> list[Application]:
        unique: dict[str, Application] = {}
        for application in applications:
            unique.setdefault(application.job_id, application)
        return list(unique.values())

    @staticmethod
    def _resume_fingerprint_from_record(record: ResumeFingerprintRecord) -> ResumeFingerprint:
        return ResumeFingerprint(
            fingerprint_id=record.id,
            user_id=record.user_id,
            resume_id=record.resume_id,
            resume_version=record.resume_version,
            content_hash=record.content_hash,
            features=record.features_json,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    @staticmethod
    def _build_progress(
        hunt_id: str,
        step_records: list[StepExecutionRecord],
    ) -> list[StepProgress]:
        by_step = {record.step_name: record for record in step_records}
        progress: list[StepProgress] = []
        for step_type in EXPECTED_STEP_ORDER:
            record = by_step.get(step_type.value)
            if record is None:
                progress.append(
                    StepProgress(
                        step=step_type,
                        status=StepProgressStatus.PENDING,
                        attempt_count=0,
                        idempotency_key=f"{hunt_id}:{step_type.value}:v1",
                        updated_at=utc_now(),
                    )
                )
                continue

            progress.append(
                StepProgress(
                    step=step_type,
                    status=StepProgressStatus(record.status),
                    attempt_count=record.attempt_count,
                    idempotency_key=record.idempotency_key,
                    started_at=record.started_at,
                    completed_at=record.completed_at,
                    updated_at=record.updated_at,
                    latency_ms=record.latency_ms,
                    last_errors=[
                        ErrorDetail(**error_payload) for error_payload in record.last_error_json
                    ],
                )
            )
        return progress

    @staticmethod
    def _count_progress(progress: list[StepProgress]) -> dict[str, int]:
        return {
            "pending_steps": sum(
                1 for item in progress if item.status == StepProgressStatus.PENDING
            ),
            "running_steps": sum(
                1 for item in progress if item.status == StepProgressStatus.RUNNING
            ),
            "completed_steps": sum(
                1 for item in progress if item.status == StepProgressStatus.COMPLETED
            ),
            "failed_steps": sum(
                1 for item in progress if item.status == StepProgressStatus.FAILED
            ),
        }

    @staticmethod
    def _floor_window(now: datetime, window_seconds: int) -> datetime:
        epoch_seconds = int(now.timestamp())
        bucket_start = epoch_seconds - (epoch_seconds % window_seconds)
        return datetime.fromtimestamp(bucket_start, tz=timezone.utc)

    @staticmethod
    def _retry_after_seconds(
        now: datetime,
        bucket_start: datetime,
        window_seconds: int,
    ) -> int:
        bucket_end = bucket_start + timedelta(seconds=window_seconds)
        return max(1, int((bucket_end - now).total_seconds()))
