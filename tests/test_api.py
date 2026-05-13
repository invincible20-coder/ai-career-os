from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

import httpx
from httpx import ASGITransport, AsyncClient

from backend.agents import AgentSuite
from backend.agents.apply_agent import ApplicationAgent
from backend.agents.tracker_agent import TrackingAgent
from backend.core.config import Settings
from backend.main import create_app
from backend.models.application import CoverLetter, ResumeContent
from backend.models.behavior import ApplicationOutcomeStatus, BehaviorType
from backend.models.career import CareerRecommendation, RoleSuggestion
from backend.models.job import Job, JobSearchResult
from backend.models.plan import ExecutionPlan, PlanStep, StepType
from backend.storage import Database
from backend.storage.records import ApplicationRecord, utc_now


class StubPlannerAgent:
    def __init__(self, plan_factory):
        self._plan_factory = plan_factory

    async def create_plan(self, goal: str) -> ExecutionPlan:
        return self._plan_factory(goal)


class StubJobFinderAgent:
    async def search(
        self,
        *,
        query: str,
        location: str | None = None,
        max_results: int | None = None,
    ) -> JobSearchResult:
        return JobSearchResult(
            query=query,
            location=location or "Remote",
            total_found=1,
            jobs=[
                Job(
                    job_id=f"{query.lower().replace(' ', '-')}-job",
                    title=f"{query} Engineer",
                    company=f"{query} Co",
                    location=location or "Remote",
                    description=f"Role for {query}",
                    requirements=["Python", "FastAPI"],
                    source="stub",
                )
            ],
        )


class ManyJobsFinderAgent:
    async def search(
        self,
        *,
        query: str,
        location: str | None = None,
        max_results: int | None = None,
    ) -> JobSearchResult:
        count = max_results or 12
        return JobSearchResult(
            query=query,
            location=location or "Remote",
            total_found=count,
            jobs=[
                Job(
                    job_id=f"{query.lower().replace(' ', '-')}-{index}",
                    title=f"{query} Engineer",
                    company=f"{query} Co {index}",
                    location=location or "Remote",
                    description=f"Backend platform role for {query}",
                    requirements=["Python", "FastAPI", "PostgreSQL"],
                    source="stub",
                )
                for index in range(count)
            ],
        )


class FailingJobFinderAgent:
    async def search(
        self,
        *,
        query: str,
        location: str | None = None,
        max_results: int | None = None,
    ) -> JobSearchResult:
        raise RuntimeError("search backend unavailable")


class FlakyJobFinderAgent:
    def __init__(self) -> None:
        self.calls = 0

    async def search(
        self,
        *,
        query: str,
        location: str | None = None,
        max_results: int | None = None,
    ) -> JobSearchResult:
        self.calls += 1
        if self.calls == 1:
            raise httpx.ReadTimeout("temporary search timeout")
        return await StubJobFinderAgent().search(
            query=query,
            location=location,
            max_results=max_results,
        )


class StubResumeAgent:
    async def generate(self, job: Job) -> ResumeContent:
        return ResumeContent(
            job_id=job.job_id,
            summary=f"Tailored summary for {job.title}",
            skills_section="Python, FastAPI",
            experience_section="Built distributed APIs",
            full_text=f"Resume for {job.title}",
        )


class StubCoverLetterAgent:
    async def generate(self, job: Job) -> CoverLetter:
        return CoverLetter(
            job_id=job.job_id,
            greeting="Dear Hiring Manager,",
            body=f"I am interested in the {job.title} role at {job.company}.",
            closing="Sincerely,",
            full_text=f"Cover letter for {job.title}",
        )


class StubCareerAgent:
    async def recommend(self, profile) -> CareerRecommendation:
        return CareerRecommendation(
            recommended_roles=[
                RoleSuggestion(
                    role="Backend Developer",
                    reason="Based on Python, APIs, and systems-building interests",
                    required_skills=["Python", "FastAPI", "Databases"],
                ),
                RoleSuggestion(
                    role="API Engineer",
                    reason="Strong alignment with API-oriented backend work",
                    required_skills=["Python", "REST APIs", "Integration Design"],
                ),
                RoleSuggestion(
                    role="Software Engineer",
                    reason="Broad engineering profile with backend signal",
                    required_skills=["Programming", "Problem Solving", "Systems Thinking"],
                ),
            ]
        )


def valid_plan(goal: str) -> ExecutionPlan:
    return ExecutionPlan(
        goal=goal,
        summary="Search, prepare, and track applications",
        steps=[
            PlanStep(step_number=1, step_type=StepType.PLAN, description="Confirm strategy"),
            PlanStep(
                step_number=2,
                step_type=StepType.SEARCH,
                description="Search matching roles",
                parameters={"query": goal, "location": "India", "max_results": 1},
            ),
            PlanStep(step_number=3, step_type=StepType.APPLY, description="Prepare applications"),
            PlanStep(step_number=4, step_type=StepType.TRACK, description="Track applications"),
        ],
    )


def invalid_plan(_: str) -> ExecutionPlan:
    return ExecutionPlan(
        goal="Broken plan",
        summary="Missing track",
        steps=[
            PlanStep(step_number=1, step_type=StepType.PLAN, description="Confirm strategy"),
            PlanStep(step_number=2, step_type=StepType.SEARCH, description="Search"),
            PlanStep(step_number=3, step_type=StepType.APPLY, description="Apply"),
        ],
    )


def build_agents(*, planner_factory, job_finder) -> AgentSuite:
    return AgentSuite(
        career_advisor=StubCareerAgent(),
        planner=StubPlannerAgent(planner_factory),
        job_finder=job_finder,
        resume_writer=StubResumeAgent(),
        cover_letter_writer=StubCoverLetterAgent(),
        application_builder=ApplicationAgent(),
        tracker=TrackingAgent(),
    )


class APITests(unittest.IsolatedAsyncioTestCase):
    async def _create_client(
        self,
        *,
        agents: AgentSuite,
        settings_overrides: dict | None = None,
    ) -> AsyncClient:
        self._tempdir = tempfile.TemporaryDirectory()
        database_path = Path(self._tempdir.name) / "test.db"
        database_url = f"sqlite+aiosqlite:///{database_path}"

        settings_kwargs = {
            "database_url": database_url,
            "cors_allowed_origins": ("http://localhost:3000",),
            "cors_allow_credentials": True,
            "openai_api_key": "test-key",
        }
        if settings_overrides:
            settings_kwargs.update(settings_overrides)

        settings = Settings(**settings_kwargs)
        database = Database(database_url)
        self._database = database
        app = create_app(settings=settings, agents=agents, database=database)

        self._lifespan = app.router.lifespan_context(app)
        await self._lifespan.__aenter__()
        self._client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        )
        return self._client

    async def asyncTearDown(self) -> None:
        if hasattr(self, "_client"):
            await self._client.aclose()
        if hasattr(self, "_lifespan"):
            await self._lifespan.__aexit__(None, None, None)
        if hasattr(self, "_tempdir"):
            self._tempdir.cleanup()

    async def _seed_application_history(
        self,
        *,
        user_key: str,
        total: int,
        role: str = "Backend Engineer",
        status: ApplicationOutcomeStatus = ApplicationOutcomeStatus.NO_RESPONSE,
        is_referral: bool = False,
    ) -> None:
        now = utc_now()
        async with self._database.session_factory() as session:
            async with session.begin():
                for index in range(total):
                    session.add(
                        ApplicationRecord(
                            application_id=f"SEED-{user_key}-{index}",
                            user_key=user_key,
                            hunt_id=f"seed-hunt-{user_key}",
                            job_id=f"seed-job-{index}",
                            role=role,
                            job_title=role,
                            company=f"Seed Co {index}",
                            platform="linkedin" if is_referral else "stub",
                            resume_version="standard-v1",
                            timestamp_applied=now,
                            application_status=status.value,
                            is_referral=is_referral,
                            status="prepared",
                            resume_json={
                                "job_id": f"seed-job-{index}",
                                "summary": "Seed summary",
                                "skills_section": "Python",
                                "experience_section": "APIs",
                                "full_text": "Seed resume",
                            },
                            cover_letter_json={
                                "job_id": f"seed-job-{index}",
                                "greeting": "Dear Hiring Manager,",
                                "body": "Seed letter",
                                "closing": "Sincerely,",
                                "full_text": "Seed letter",
                            },
                            notes="Seeded behavior history",
                            created_at=now,
                            submitted_at=None,
                        )
                    )

    async def test_invalid_plan_returns_400_with_failure_envelope(self) -> None:
        client = await self._create_client(
            agents=build_agents(
                planner_factory=invalid_plan,
                job_finder=StubJobFinderAgent(),
            )
        )

        response = await client.post(
            "/api/v1/hunts",
            json={"goal": "Backend Engineer"},
        )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertFalse(payload["success"])
        self.assertIsNone(payload["data"])
        self.assertTrue(any(error["code"] == "missing_plan_step" for error in payload["errors"]))

    async def test_step_failure_returns_500_with_failure_envelope(self) -> None:
        client = await self._create_client(
            agents=build_agents(
                planner_factory=valid_plan,
                job_finder=FailingJobFinderAgent(),
            )
        )

        response = await client.post(
            "/api/v1/hunts",
            json={"goal": "Backend Engineer"},
        )

        self.assertEqual(response.status_code, 500)
        payload = response.json()
        self.assertFalse(payload["success"])
        self.assertIsNone(payload["data"])
        self.assertTrue(any(error["step"] == "search" for error in payload["errors"]))

    async def test_invalid_input_returns_400(self) -> None:
        client = await self._create_client(
            agents=build_agents(
                planner_factory=valid_plan,
                job_finder=StubJobFinderAgent(),
            )
        )

        response = await client.post("/api/v1/hunts", json={"goal": "a"})

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertFalse(payload["success"])
        self.assertTrue(any(error["code"] == "invalid_request" for error in payload["errors"]))

    async def test_recommend_career_endpoint_returns_structured_roles(self) -> None:
        client = await self._create_client(
            agents=build_agents(
                planner_factory=valid_plan,
                job_finder=StubJobFinderAgent(),
            )
        )

        response = await client.post(
            "/api/v1/recommend-career",
            json={
                "skills": ["Python", "APIs"],
                "interests": ["building systems"],
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertEqual(
            [role["role"] for role in payload["data"]["recommended_roles"]],
            ["Backend Developer", "API Engineer", "Software Engineer"],
        )

    async def test_vague_goal_uses_career_recommendation_before_planning(self) -> None:
        client = await self._create_client(
            agents=build_agents(
                planner_factory=valid_plan,
                job_finder=StubJobFinderAgent(),
            )
        )

        response = await client.post(
            "/api/v1/hunts",
            json={
                "goal": "not sure",
                "skills": ["Python", "APIs"],
                "interests": ["building systems"],
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["data"]["goal"], "Backend Developer")
        self.assertEqual(payload["data"]["original_goal"], "not sure")
        self.assertTrue(payload["data"]["goal_was_recommended"])
        self.assertEqual(
            payload["data"]["career_recommendation"]["recommended_roles"][0]["role"],
            "Backend Developer",
        )
        self.assertEqual(
            payload["data"]["jobs_found"][0]["company"],
            "Backend Developer Co",
        )
        self.assertEqual(payload["data"]["summary"]["completed_steps"], 4)
        self.assertEqual(payload["data"]["summary"]["failed_steps"], 0)

    async def test_missing_goal_and_profile_returns_400(self) -> None:
        client = await self._create_client(
            agents=build_agents(
                planner_factory=valid_plan,
                job_finder=StubJobFinderAgent(),
            )
        )

        response = await client.post("/api/v1/hunts", json={})

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertFalse(payload["success"])
        self.assertTrue(
            any(error["code"] == "missing_goal_or_profile" for error in payload["errors"])
        )

    async def test_hunt_response_exposes_completed_progress_state(self) -> None:
        client = await self._create_client(
            agents=build_agents(
                planner_factory=valid_plan,
                job_finder=StubJobFinderAgent(),
            )
        )

        response = await client.post("/api/v1/hunts", json={"goal": "Backend Engineer"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(len(payload["progress"]), 4)
        self.assertTrue(all(item["status"] == "completed" for item in payload["progress"]))
        self.assertEqual(payload["summary"]["completed_steps"], 4)
        self.assertEqual(payload["summary"]["failed_steps"], 0)

        snapshot_response = await client.get(f"/api/v1/hunts/{payload['hunt_id']}")
        self.assertEqual(snapshot_response.status_code, 200)
        snapshot = snapshot_response.json()["data"]
        self.assertEqual(snapshot["hunt_id"], payload["hunt_id"])
        self.assertEqual(snapshot["summary"]["completed_steps"], 4)
        self.assertTrue(all(item["status"] == "completed" for item in snapshot["progress"]))

    async def test_behavior_endpoints_return_metrics_and_strategy(self) -> None:
        user_key = "behavior-user"
        client = await self._create_client(
            agents=build_agents(
                planner_factory=valid_plan,
                job_finder=StubJobFinderAgent(),
            )
        )

        hunt_response = await client.post(
            "/api/v1/hunts",
            json={"goal": "Backend Engineer"},
            headers={"x-user-id": user_key},
        )
        self.assertEqual(hunt_response.status_code, 200)

        profile_response = await client.get(
            "/api/v1/behavior-profile",
            headers={"x-user-id": user_key},
        )
        strategy_response = await client.get(
            "/api/v1/strategy",
            headers={"x-user-id": user_key},
        )
        analytics_response = await client.get(
            "/api/v1/analytics",
            headers={"x-user-id": user_key},
        )

        self.assertEqual(profile_response.status_code, 200)
        self.assertEqual(strategy_response.status_code, 200)
        self.assertEqual(analytics_response.status_code, 200)

        profile = profile_response.json()["data"]
        strategy = strategy_response.json()["data"]
        analytics = analytics_response.json()["data"]

        self.assertEqual(profile["classification"], BehaviorType.INSUFFICIENT_DATA.value)
        self.assertEqual(profile["metrics"]["total_applications"], 1)
        self.assertEqual(profile["metrics"]["platform_distribution"], {"stub": 1})
        self.assertEqual(strategy["behavior_type"], BehaviorType.INSUFFICIENT_DATA.value)
        self.assertEqual(analytics["metrics"]["total_applications"], 1)
        self.assertEqual(analytics["top_platforms"][0]["name"], "stub")

    async def test_mass_applier_strategy_reduces_application_volume(self) -> None:
        user_key = "mass-user"
        client = await self._create_client(
            agents=build_agents(
                planner_factory=valid_plan,
                job_finder=ManyJobsFinderAgent(),
            ),
            settings_overrides={
                "hunt_rate_limit_requests": 100,
                "max_jobs_per_search": 20,
            },
        )
        await self._seed_application_history(user_key=user_key, total=16)

        strategy_response = await client.get(
            "/api/v1/strategy",
            headers={"x-user-id": user_key},
        )
        self.assertEqual(strategy_response.status_code, 200)
        self.assertEqual(
            strategy_response.json()["data"]["behavior_type"],
            BehaviorType.MASS_APPLIER.value,
        )

        hunt_response = await client.post(
            "/api/v1/hunts",
            json={"goal": "Backend Engineer"},
            headers={"x-user-id": user_key},
        )

        self.assertEqual(hunt_response.status_code, 200)
        payload = hunt_response.json()["data"]
        self.assertEqual(len(payload["jobs_found"]), 5)
        self.assertEqual(len(payload["applications"]), 5)
        self.assertTrue(
            all(
                application["resume_version"] == "targeted-v1"
                for application in payload["applications"]
            )
        )

    async def test_transient_search_failure_retries_without_duplicate_state(self) -> None:
        client = await self._create_client(
            agents=build_agents(
                planner_factory=valid_plan,
                job_finder=FlakyJobFinderAgent(),
            )
        )

        response = await client.post("/api/v1/hunts", json={"goal": "Platform Engineer"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        search_progress = next(
            item for item in payload["progress"] if item["step"] == StepType.SEARCH.value
        )
        self.assertEqual(search_progress["attempt_count"], 2)
        self.assertEqual(search_progress["status"], "completed")
        self.assertEqual(len(payload["jobs_found"]), 1)
        self.assertEqual(len(payload["applications"]), 1)

    async def test_hunts_endpoint_rate_limits_by_client(self) -> None:
        client = await self._create_client(
            agents=build_agents(
                planner_factory=valid_plan,
                job_finder=StubJobFinderAgent(),
            ),
            settings_overrides={
                "hunt_rate_limit_requests": 1,
                "hunt_rate_limit_window_seconds": 60,
            },
        )

        headers = {"x-forwarded-for": "203.0.113.10"}
        first_response = await client.post(
            "/api/v1/hunts",
            json={"goal": "Backend Engineer"},
            headers=headers,
        )
        second_response = await client.post(
            "/api/v1/hunts",
            json={"goal": "Data Engineer"},
            headers=headers,
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 429)
        payload = second_response.json()
        self.assertFalse(payload["success"])
        self.assertTrue(any(error["code"] == "rate_limit_exceeded" for error in payload["errors"]))

    async def test_concurrent_hunts_remain_isolated(self) -> None:
        client = await self._create_client(
            agents=build_agents(
                planner_factory=valid_plan,
                job_finder=StubJobFinderAgent(),
            )
        )

        goals = [
            "Platform Engineer",
            "Data Engineer",
            "Backend Engineer",
        ]

        responses = await asyncio.gather(
            *(client.post("/api/v1/hunts", json={"goal": goal}) for goal in goals)
        )

        payloads = [response.json() for response in responses]
        hunt_ids = [payload["data"]["hunt_id"] for payload in payloads]

        self.assertEqual(len(hunt_ids), len(set(hunt_ids)))

        for goal, payload in zip(goals, payloads, strict=False):
            self.assertTrue(payload["success"])
            self.assertEqual(payload["data"]["goal"], goal)
            self.assertEqual(len(payload["data"]["jobs_found"]), 1)
            self.assertEqual(len(payload["data"]["applications"]), 1)
            self.assertTrue(
                all(job["hunt_id"] == payload["data"]["hunt_id"] for job in payload["data"]["jobs_found"])
            )
            self.assertTrue(
                all(
                    application["hunt_id"] == payload["data"]["hunt_id"]
                    for application in payload["data"]["applications"]
                )
            )
            self.assertEqual(
                payload["data"]["jobs_found"][0]["company"],
                f"{goal} Co",
            )

        snapshots = await asyncio.gather(
            *(client.get(f"/api/v1/hunts/{hunt_id}") for hunt_id in hunt_ids)
        )
        for goal, hunt_id, response in zip(goals, hunt_ids, snapshots, strict=False):
            self.assertEqual(response.status_code, 200)
            snapshot = response.json()["data"]
            self.assertEqual(snapshot["hunt_id"], hunt_id)
            self.assertEqual(snapshot["jobs_found"][0]["company"], f"{goal} Co")
