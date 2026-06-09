from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from backend.core.config import Settings
from backend.main import create_app
from backend.models.abc import BehaviorEventType, OutcomeType
from backend.models.job import Job
from backend.services.event_bus import EventBus
from backend.services.trust_service import JobTrustService
from backend.storage import Database
from tests.test_api import build_agents, valid_plan, StubJobFinderAgent


class CompletedSystemTests(unittest.IsolatedAsyncioTestCase):
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
        app = create_app(
            settings=settings,
            agents=build_agents(planner_factory=valid_plan, job_finder=StubJobFinderAgent()),
            database=database,
        )
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

    async def test_resume_report_returns_semantics_weaknesses_and_predictions(self) -> None:
        client = await self._create_client()
        response = await client.post(
            "/api/v1/resume-intelligence/report",
            params={"user_id": "resume-report-user"},
            json={
                "resume_id": "resume-v1",
                "resume_version": "v1",
                "target_role": "Backend Engineer",
                "content": (
                    "Skills\nPython FastAPI SQL\nExperience\n"
                    "- responsible for APIs\n"
                    "- worked on services\n"
                    "Education\nBachelor of Engineering"
                ),
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertIn("Python", data["semantic_profile"]["skills"])
        self.assertTrue(data["weaknesses"])
        self.assertIn("interview_probability", data["optimization_prediction"])
        self.assertGreaterEqual(data["ats"]["final_score"], 0)

    async def test_recommendations_expose_signal_breakdown_and_ignore_event(self) -> None:
        client = await self._create_client()
        job = Job(
            job_id="backend-job",
            title="Backend Engineer",
            company="Systems Co",
            location="Remote",
            description="Build backend APIs and services.",
            requirements=["Python", "FastAPI"],
            source="stub",
        )
        rank_response = await client.post(
            "/api/v1/abc/recommendations",
            json={
                "user_id": "explain-user",
                "goal": "Backend Engineer",
                "jobs": [job.model_dump(mode="json")],
            },
        )
        self.assertEqual(rank_response.status_code, 200)
        recommendation = rank_response.json()["data"]["recommendations"][0]
        self.assertIn("signal_breakdown", recommendation)
        self.assertIn("explanation", recommendation)
        self.assertIn("uncertainty_percent", recommendation)

        behavior_response = await client.post(
            "/api/v1/abc/behavior-events",
            json={
                "antecedent_event_id": recommendation["event_id"],
                "event_type": BehaviorEventType.JOB_IGNORED.value,
            },
        )
        self.assertEqual(behavior_response.status_code, 200)

    async def test_auth_identity_graph_persists_provider_intelligence(self) -> None:
        client = await self._create_client()
        register = await client.post(
            "/api/v1/auth/register",
            json={"email": "identity@example.com", "password": "safe-password-123"},
        )
        self.assertEqual(register.status_code, 200)
        user_id = register.json()["id"]

        link = await client.post(
            f"/api/v1/auth/oauth/link-local/{user_id}",
            json={
                "provider": "github",
                "provider_account_id": "gh-123",
                "metadata": {
                    "languages": {"Python": 70, "TypeScript": 30},
                    "repositories": ["fastapi-api", "distributed-service"],
                },
            },
        )
        self.assertEqual(link.status_code, 200)
        graph = await client.get(f"/api/v1/auth/identity-graph/{user_id}")
        self.assertEqual(graph.status_code, 200)
        self.assertIn("github", graph.json()["provider_intelligence"])

    async def test_metrics_and_security_headers_are_visible(self) -> None:
        client = await self._create_client()
        health = await client.get("/api/v1/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.headers["x-content-type-options"], "nosniff")

        metrics = await client.get("/api/v1/metrics")
        self.assertEqual(metrics.status_code, 200)
        self.assertIn("requests", metrics.json()["data"])


class InfrastructureUnitTests(unittest.IsolatedAsyncioTestCase):
    async def test_event_bus_streams_published_events(self) -> None:
        bus = EventBus()
        stream = bus.subscribe("hunt-1")
        first = await stream.__anext__()
        await bus.publish("hunt-1", {"type": "step_started", "step": "search"})
        second = await stream.__anext__()
        await stream.aclose()

        self.assertIn("stream_connected", first)
        self.assertIn("step_started", second)

    def test_trust_service_flags_scam_and_deduplicates(self) -> None:
        service = JobTrustService()
        jobs = service.enrich_jobs(
            [
                {
                    "title": "Backend Engineer",
                    "company": "Real Co",
                    "location": "Remote",
                    "description": "Build APIs with Python and databases.",
                    "requirements": ["Python", "API"],
                    "url": "https://real.example/jobs/1",
                    "source": "company_site",
                },
                {
                    "title": "Backend Engineer",
                    "company": "Real Co",
                    "location": "Remote",
                    "description": "Build APIs with Python and databases.",
                    "requirements": ["Python", "API"],
                    "url": "https://real.example/jobs/2",
                    "source": "company_site",
                },
                {
                    "title": "Guaranteed Job",
                    "company": "Suspicious",
                    "location": "Remote",
                    "description": "Guaranteed job, registration fee required, telegram recruiter.",
                    "requirements": ["No interview"],
                    "url": "ftp://bad.example",
                    "source": "unknown",
                },
            ]
        )

        self.assertEqual(len(jobs), 2)
        suspicious = next(job for job in jobs if job["company"] == "Suspicious")
        self.assertTrue(suspicious["scam_flags"])
        self.assertLess(suspicious["trust_score"], 0.5)
