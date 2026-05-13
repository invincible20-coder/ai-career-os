from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from backend.agents import AgentSuite
from backend.agents.apply_agent import ApplicationAgent
from backend.agents.tracker_agent import TrackingAgent
from backend.core.config import Settings
from backend.main import create_app
from backend.models.abc import BehaviorEventType, OutcomeType
from backend.models.job import Job, JobSearchResult
from backend.storage import Database
from tests.test_api import (
    StubCareerAgent,
    StubCoverLetterAgent,
    StubPlannerAgent,
    StubResumeAgent,
    valid_plan,
)


class EqualCandidateJobFinder:
    async def search(
        self,
        *,
        query: str,
        location: str | None = None,
        max_results: int | None = None,
    ) -> JobSearchResult:
        jobs = _candidate_jobs()
        return JobSearchResult(
            query=query,
            location=location or "Remote",
            total_found=len(jobs),
            jobs=jobs,
        )


def _candidate_jobs() -> list[Job]:
    return [
        Job(
            job_id="backend-job",
            title="Software Engineer",
            company="Backend Systems Co",
            location="Remote",
            description="Build backend APIs, databases, and platform services.",
            requirements=["software", "api", "backend", "database"],
            source="stub",
        ),
        Job(
            job_id="frontend-job",
            title="Software Engineer",
            company="Frontend Product Co",
            location="Remote",
            description="Build frontend React UI, web surfaces, and product workflows.",
            requirements=["software", "react", "frontend", "ui"],
            source="stub",
        ),
    ]


def _agents() -> AgentSuite:
    return AgentSuite(
        career_advisor=StubCareerAgent(),
        planner=StubPlannerAgent(valid_plan),
        job_finder=EqualCandidateJobFinder(),
        resume_writer=StubResumeAgent(),
        cover_letter_writer=StubCoverLetterAgent(),
        application_builder=ApplicationAgent(),
        tracker=TrackingAgent(),
    )


class ABCAdaptiveTests(unittest.IsolatedAsyncioTestCase):
    async def _create_client(self) -> AsyncClient:
        self._tempdir = tempfile.TemporaryDirectory()
        database_path = Path(self._tempdir.name) / "test.db"
        database_url = f"sqlite+aiosqlite:///{database_path}"
        settings = Settings(
            database_url=database_url,
            cors_allowed_origins=("http://localhost:3000",),
            cors_allow_credentials=True,
            max_jobs_per_search=10,
            hunt_rate_limit_requests=100,
        )
        database = Database(database_url)
        self._database = database
        app = create_app(settings=settings, agents=_agents(), database=database)
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

    async def _rank(self, client: AsyncClient, user_id: str) -> list[dict]:
        response = await client.post(
            "/api/v1/abc/recommendations",
            json={
                "user_id": user_id,
                "goal": "Software Engineer",
                "hunt_id": f"hunt-{user_id}",
                "session_id": f"session-{user_id}",
                "jobs": [job.model_dump(mode="json") for job in _candidate_jobs()],
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        return payload["data"]["recommendations"]

    async def _teach(
        self,
        client: AsyncClient,
        *,
        user_id: str,
        category: str,
        outcome_type: OutcomeType,
        count: int,
    ) -> None:
        recommendations = await self._rank(client, user_id)
        antecedent_id = next(
            item["event_id"]
            for item in recommendations
            if item["job_category"] == category
        )
        for _ in range(count):
            behavior_response = await client.post(
                "/api/v1/abc/behavior-events",
                json={
                    "antecedent_event_id": antecedent_id,
                    "event_type": BehaviorEventType.APPLICATION_COMPLETED.value,
                    "resume_id": "resume-v1",
                },
            )
            self.assertEqual(behavior_response.status_code, 200)
            behavior_id = behavior_response.json()["data"]["event_id"]
            outcome_response = await client.post(
                "/api/v1/abc/outcomes",
                json={
                    "behavior_event_id": behavior_id,
                    "outcome_type": outcome_type.value,
                    "response_time_days": 3,
                },
            )
            self.assertEqual(outcome_response.status_code, 200)

    async def test_new_user_uses_neutral_weights_and_base_match(self) -> None:
        client = await self._create_client()

        response = await client.post(
            "/api/v1/abc/recommendations",
            json={
                "user_id": "new-user",
                "goal": "Backend Engineer",
                "jobs": [job.model_dump(mode="json") for job in _candidate_jobs()],
            },
        )

        self.assertEqual(response.status_code, 200)
        recommendations = response.json()["data"]["recommendations"]
        self.assertEqual(recommendations[0]["job_id"], "backend-job")
        self.assertEqual(recommendations[0]["category_weight"], 0.5)
        self.assertIn("Cold start", recommendations[0]["reason"])

    async def test_backend_interviews_raise_backend_jobs(self) -> None:
        client = await self._create_client()
        await self._teach(
            client,
            user_id="backend-success-user",
            category="backend",
            outcome_type=OutcomeType.INTERVIEW,
            count=5,
        )

        recommendations = await self._rank(client, "backend-success-user")
        profile_response = await client.get(
            "/api/v1/abc/strategy-profile",
            params={"user_id": "backend-success-user"},
        )

        self.assertEqual(recommendations[0]["job_category"], "backend")
        profile = profile_response.json()["data"]
        self.assertGreater(
            profile["category_weights"]["backend"],
            profile["category_weights"]["frontend"],
        )

    async def test_frontend_no_responses_decrease_frontend_jobs(self) -> None:
        client = await self._create_client()
        await self._teach(
            client,
            user_id="frontend-no-response-user",
            category="frontend",
            outcome_type=OutcomeType.NO_RESPONSE,
            count=6,
        )

        recommendations = await self._rank(client, "frontend-no-response-user")
        frontend = next(item for item in recommendations if item["job_category"] == "frontend")
        backend = next(item for item in recommendations if item["job_category"] == "backend")

        self.assertLess(frontend["final_score"], backend["final_score"])
        self.assertLess(frontend["category_weight"], 0.5)

    async def test_opposite_histories_produce_different_rankings(self) -> None:
        client = await self._create_client()
        await self._teach(
            client,
            user_id="backend-user",
            category="backend",
            outcome_type=OutcomeType.INTERVIEW,
            count=5,
        )
        await self._teach(
            client,
            user_id="frontend-user",
            category="frontend",
            outcome_type=OutcomeType.INTERVIEW,
            count=5,
        )

        backend_user_ranking = await self._rank(client, "backend-user")
        frontend_user_ranking = await self._rank(client, "frontend-user")

        self.assertEqual(backend_user_ranking[0]["job_category"], "backend")
        self.assertEqual(frontend_user_ranking[0]["job_category"], "frontend")
        self.assertNotEqual(
            backend_user_ranking[0]["job_id"],
            frontend_user_ranking[0]["job_id"],
        )

    async def test_outcome_requires_existing_behavior_event(self) -> None:
        client = await self._create_client()

        response = await client.post(
            "/api/v1/abc/outcomes",
            json={
                "behavior_event_id": "missing-behavior",
                "outcome_type": OutcomeType.INTERVIEW.value,
                "response_time_days": 4,
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.json()["success"])
