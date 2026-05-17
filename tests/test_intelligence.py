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


class IntelligenceJobFinder:
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
            title="Backend Engineer",
            company="Backend Systems Co",
            location="Remote",
            description="Build backend APIs and distributed systems.",
            requirements=["Python", "FastAPI", "PostgreSQL"],
            source="stub",
        ),
        Job(
            job_id="frontend-job",
            title="Frontend Engineer",
            company="Frontend Product Co",
            location="Remote",
            description="Build React interfaces and product workflows.",
            requirements=["React", "TypeScript", "CSS"],
            source="stub",
        ),
        Job(
            job_id="data-job",
            title="Data Analyst",
            company="Data Insight Co",
            location="Remote",
            description="Analyze SQL datasets and build reporting pipelines.",
            requirements=["SQL", "Python", "Analytics"],
            source="stub",
        ),
    ]


def _agents() -> AgentSuite:
    return AgentSuite(
        career_advisor=StubCareerAgent(),
        planner=StubPlannerAgent(valid_plan),
        job_finder=IntelligenceJobFinder(),
        resume_writer=StubResumeAgent(),
        cover_letter_writer=StubCoverLetterAgent(),
        application_builder=ApplicationAgent(),
        tracker=TrackingAgent(),
    )


class IntelligenceTests(unittest.IsolatedAsyncioTestCase):
    async def _create_client(self) -> AsyncClient:
        self._tempdir = tempfile.TemporaryDirectory()
        database_path = Path(self._tempdir.name) / "test.db"
        database_url = f"sqlite+aiosqlite:///{database_path}"
        settings = Settings(
            database_url=database_url,
            cors_allowed_origins=("http://localhost:3000",),
            cors_allow_credentials=True,
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

    async def _rank(self, client: AsyncClient, user_id: str, *, profile: dict | None = None) -> list[dict]:
        response = await client.post(
            "/api/v1/abc/recommendations",
            json={
                "user_id": user_id,
                "goal": "Software Engineer",
                "hunt_id": f"hunt-{user_id}",
                "session_id": f"session-{user_id}",
                "profile": profile,
                "jobs": [job.model_dump(mode="json") for job in _candidate_jobs()],
            },
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["data"]["recommendations"]

    async def _teach_backend_success(self, client: AsyncClient, user_id: str, *, count: int) -> None:
        recommendations = await self._rank(client, user_id)
        antecedent_id = next(
            item["event_id"]
            for item in recommendations
            if item["job_category"] == "backend"
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
            behavior_id = behavior_response.json()["data"]["event_id"]
            outcome_response = await client.post(
                "/api/v1/abc/outcomes",
                json={
                    "behavior_event_id": behavior_id,
                    "outcome_type": OutcomeType.INTERVIEW.value,
                    "response_time_days": 3,
                },
            )
            self.assertEqual(outcome_response.status_code, 200)

    async def test_confused_user_stays_in_exploration_mode(self) -> None:
        client = await self._create_client()

        intent_response = await client.post(
            "/api/v1/intelligence/intent",
            params={"user_id": "confused-user"},
            json={"message": "I don't know what to do anymore."},
        )
        discovery_response = await client.post(
            "/api/v1/intelligence/career-discovery",
            params={"user_id": "confused-user"},
            json={},
        )
        confidence_response = await client.post(
            "/api/v1/intelligence/confidence",
            params={"user_id": "confused-user"},
            json={},
        )

        intent = intent_response.json()["data"]
        discovery = discovery_response.json()["data"]
        confidence = confidence_response.json()["data"]
        self.assertTrue(intent["exploration_mode"])
        self.assertGreater(intent["uncertainty"], intent["career_clarity"])
        self.assertTrue(discovery["exploration_mode"])
        self.assertGreaterEqual(len(discovery["career_paths"]), 3)
        self.assertTrue(confidence["exploration_mode"])
        self.assertLess(confidence["confidence"], 0.55)

    async def test_strong_backend_user_gains_confidence_and_backend_rank(self) -> None:
        client = await self._create_client()
        profile = {
            "skills": ["Python", "FastAPI"],
            "education": "Computer Science",
            "interests": ["APIs", "distributed systems"],
            "experience": "Built backend systems",
            "preferred_locations": ["Remote"],
        }
        await client.post(
            "/api/v1/intelligence/intent",
            params={"user_id": "backend-user"},
            json={"message": "I like APIs and backend systems.", "profile": profile},
        )
        await self._teach_backend_success(client, "backend-user", count=12)

        recommendations = await self._rank(client, "backend-user", profile=profile)
        confidence_response = await client.post(
            "/api/v1/intelligence/confidence",
            params={"user_id": "backend-user"},
            json=profile,
        )

        confidence = confidence_response.json()["data"]
        self.assertEqual(recommendations[0]["job_category"], "backend")
        self.assertGreater(confidence["confidence"], 0.55)
        self.assertFalse(confidence["exploration_mode"])

    async def test_inconsistent_user_retains_lower_confidence(self) -> None:
        client = await self._create_client()
        profile = {"skills": ["Python"], "interests": ["APIs", "design"]}
        for message in [
            "I want backend roles.",
            "Maybe I should try product design.",
            "I don't know what I want anymore.",
        ]:
            await client.post(
                "/api/v1/intelligence/intent",
                params={"user_id": "inconsistent-user"},
                json={"message": message, "profile": profile},
            )

        confidence_response = await client.post(
            "/api/v1/intelligence/confidence",
            params={"user_id": "inconsistent-user"},
            json=profile,
        )
        state_response = await client.get(
            "/api/v1/intelligence/profile",
            params={"user_id": "inconsistent-user"},
        )

        confidence = confidence_response.json()["data"]
        state = state_response.json()["data"]
        self.assertTrue(confidence["exploration_mode"])
        self.assertLess(confidence["confidence"], 0.55)
        self.assertEqual(state["conversation_count"], 3)

    async def test_sparse_user_uses_neutral_weights_and_broad_discovery(self) -> None:
        client = await self._create_client()

        recommendations = await self._rank(client, "sparse-user")
        discovery_response = await client.post(
            "/api/v1/intelligence/career-discovery",
            params={"user_id": "sparse-user"},
            json={},
        )
        confidence_response = await client.post(
            "/api/v1/intelligence/confidence",
            params={"user_id": "sparse-user"},
            json={},
        )

        discovery = discovery_response.json()["data"]
        confidence = confidence_response.json()["data"]
        self.assertEqual(recommendations[0]["category_weight"], 0.5)
        self.assertTrue(discovery["exploration_mode"])
        self.assertGreaterEqual(len(discovery["career_paths"]), 3)
        self.assertTrue(confidence["exploration_mode"])
