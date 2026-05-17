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
from backend.models.application import CoverLetter, ResumeContent
from backend.models.job import Job, JobSearchResult
from backend.storage import Database
from tests.test_api import StubCareerAgent, StubPlannerAgent, valid_plan


class CyclingResumeAgent:
    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, job: Job) -> ResumeContent:
        self.calls += 1
        if self.calls % 2:
            full_text = (
                "Backend engineer\n"
                "- built APIs\n"
                "- worked with Python\n"
                "Bachelor of Engineering"
            )
        else:
            full_text = (
                "Backend engineer with 5 years experience\n"
                "- designed scalable distributed APIs reducing latency 35%\n"
                "- optimized PostgreSQL queries increasing throughput 42%\n"
                "- led cross-functional delivery of FastAPI microservices\n"
                "Bachelor of Engineering in Computer Science"
            )
        return ResumeContent(
            job_id=job.job_id,
            summary="Backend resume",
            skills_section="Python, FastAPI, PostgreSQL",
            experience_section="Built APIs",
            full_text=full_text,
        )


class StubCoverLetterAgent:
    async def generate(self, job: Job) -> CoverLetter:
        return CoverLetter(
            job_id=job.job_id,
            body=f"Interested in {job.title}",
            full_text=f"Cover letter for {job.title}",
        )


class MixedJobFinder:
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
            total_found=2,
            jobs=[
                Job(
                    job_id=f"{query}-backend",
                    title="Backend Engineer",
                    company="Backend Co",
                    location="Remote",
                    description="Build backend APIs and distributed services.",
                    requirements=["Python", "FastAPI", "PostgreSQL"],
                    source="stub",
                ),
                Job(
                    job_id=f"{query}-frontend",
                    title="Frontend Engineer",
                    company="Frontend Co",
                    location="Remote",
                    description="Build React interfaces.",
                    requirements=["React", "TypeScript", "CSS"],
                    source="stub",
                ),
            ],
        )


def _agents() -> AgentSuite:
    return AgentSuite(
        career_advisor=StubCareerAgent(),
        planner=StubPlannerAgent(valid_plan),
        job_finder=MixedJobFinder(),
        resume_writer=CyclingResumeAgent(),
        cover_letter_writer=StubCoverLetterAgent(),
        application_builder=ApplicationAgent(),
        tracker=TrackingAgent(),
    )


class ResumePredictionTests(unittest.IsolatedAsyncioTestCase):
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

    async def _hunt(self, client: AsyncClient, user_id: str) -> dict:
        response = await client.post(
            "/api/v1/hunts",
            headers={"x-user-id": user_id},
            json={
                "goal": "Backend Engineer",
                "skills": ["Python", "FastAPI"],
                "interests": ["APIs"],
            },
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["data"]

    async def _complete_outcome(
        self,
        client: AsyncClient,
        *,
        hunt: dict,
        outcome: OutcomeType,
    ) -> None:
        job = hunt["jobs_found"][0]
        behavior_response = await client.post(
            "/api/v1/abc/behavior-events",
            json={
                "antecedent_event_id": job["recommendation_event_id"],
                "event_type": BehaviorEventType.APPLICATION_COMPLETED.value,
            },
        )
        self.assertEqual(behavior_response.status_code, 200)
        behavior_id = behavior_response.json()["data"]["event_id"]
        outcome_response = await client.post(
            "/api/v1/abc/outcomes",
            json={
                "behavior_event_id": behavior_id,
                "outcome_type": outcome.value,
                "response_time_days": 3,
            },
        )
        self.assertEqual(outcome_response.status_code, 200)

    async def test_strong_backend_resume_increases_effectiveness_and_compatibility(self) -> None:
        client = await self._create_client()
        baseline_prediction = await client.get(
            "/api/v1/predictive-career/profile",
            params={"user_id": "backend-user"},
        )
        baseline_backend = next(
            item
            for item in baseline_prediction.json()["data"]["predictions"]
            if item["category"] == "backend"
        )

        for _ in range(6):
            hunt = await self._hunt(client, "backend-user")
            await self._complete_outcome(client, hunt=hunt, outcome=OutcomeType.INTERVIEW)

        correlations = await client.get(
            "/api/v1/resume-intelligence/correlations",
            params={"user_id": "backend-user"},
        )
        prediction = await client.get(
            "/api/v1/predictive-career/profile",
            params={"user_id": "backend-user"},
        )
        backend_prediction = next(
            item
            for item in prediction.json()["data"]["predictions"]
            if item["category"] == "backend"
        )
        effectiveness = list(correlations.json()["data"]["resume_effectiveness"].values())

        self.assertTrue(effectiveness)
        self.assertGreater(max(item["effectiveness_score"] for item in effectiveness), 0.45)
        self.assertGreater(
            backend_prediction["compatibility"],
            baseline_backend["compatibility"],
        )

    async def test_sparse_data_keeps_low_confidence(self) -> None:
        client = await self._create_client()
        for _ in range(2):
            hunt = await self._hunt(client, "sparse-user")
            await self._complete_outcome(client, hunt=hunt, outcome=OutcomeType.INTERVIEW)

        correlations = await client.get(
            "/api/v1/resume-intelligence/correlations",
            params={"user_id": "sparse-user"},
        )
        predictions = await client.get(
            "/api/v1/predictive-career/profile",
            params={"user_id": "sparse-user"},
        )

        quantified = correlations.json()["data"]["feature_correlations"]["quantified_achievements"]
        top_prediction = predictions.json()["data"]["predictions"][0]
        self.assertLess(quantified["confidence"], 0.25)
        self.assertGreater(quantified["uncertainty"], 0.75)
        self.assertLess(top_prediction["confidence"], 0.55)

    async def test_inconsistent_user_has_unstable_trajectory(self) -> None:
        client = await self._create_client()
        for message in [
            "I want backend roles.",
            "Maybe product design is better.",
            "I don't know what I want anymore.",
        ]:
            await client.post(
                "/api/v1/intelligence/intent",
                params={"user_id": "inconsistent-user"},
                json={"message": message},
            )

        predictions = await client.get(
            "/api/v1/predictive-career/profile",
            params={"user_id": "inconsistent-user"},
        )
        top_prediction = predictions.json()["data"]["predictions"][0]
        self.assertLess(top_prediction["trajectory_stability"], 0.45)
        self.assertLess(top_prediction["confidence"], 0.4)

    async def test_resume_improvement_updates_quantified_correlation(self) -> None:
        client = await self._create_client()

        weak_hunt = await self._hunt(client, "resume-user")
        await self._complete_outcome(client, hunt=weak_hunt, outcome=OutcomeType.NO_RESPONSE)
        before = await client.get(
            "/api/v1/resume-intelligence/correlations",
            params={"user_id": "resume-user"},
        )
        before_value = before.json()["data"]["feature_correlations"]["quantified_achievements"][
            "interview_correlation"
        ]

        for _ in range(5):
            strong_hunt = await self._hunt(client, "resume-user")
            await self._complete_outcome(client, hunt=strong_hunt, outcome=OutcomeType.INTERVIEW)

        after = await client.get(
            "/api/v1/resume-intelligence/correlations",
            params={"user_id": "resume-user"},
        )
        after_value = after.json()["data"]["feature_correlations"]["quantified_achievements"][
            "interview_correlation"
        ]

        self.assertGreater(after_value, before_value)
