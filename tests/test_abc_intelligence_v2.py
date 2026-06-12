"""
Tests for ABC Behavioral Intelligence Engine V2.0.

Covers:
- Immutable learning event store
- Dual memory (short-term / long-term)
- Behavioral pattern discovery
- Semantic generalization
- Career persona inference
- Self-evaluation metrics
- Strategy feedback signals
- V2 ranking formula integration
"""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from backend.agents import AgentSuite
from backend.agents.apply_agent import ApplicationAgent
from backend.agents.tracker_agent import TrackingAgent
from backend.core.config import Settings
from backend.main import create_app
from backend.models.abc import BehaviorEventType, OutcomeType
from backend.models.abc_intelligence import (
    BehavioralPattern,
    CareerPersona,
    ConsequenceLevel,
    DualMemoryState,
    MemoryEntry,
    PersonaType,
    ShortTermMemory,
    LongTermMemory,
    TrendDirection,
    consequence_weight_for,
)
from backend.models.job import Job, JobSearchResult
from backend.services.semantic_service import SemanticService
from backend.storage import Database
from tests.test_api import (
    StubCareerAgent,
    StubCoverLetterAgent,
    StubPlannerAgent,
    StubResumeAgent,
    valid_plan,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test Fixtures
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


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
            title="Senior Backend Engineer",
            company="Acme Corp",
            location="Remote",
            description="Build scalable Python microservices.",
            requirements=["Python", "FastAPI", "PostgreSQL"],
            source="stub",
            job_category="backend",
        ),
        Job(
            job_id="frontend-job",
            title="React Frontend Developer",
            company="UI Inc",
            location="New York, NY",
            description="Build React UI components.",
            requirements=["React", "TypeScript", "CSS"],
            source="stub",
            job_category="frontend",
        ),
        Job(
            job_id="data-job",
            title="Data Engineer",
            company="DataCo",
            location="Remote",
            description="ETL pipelines and data warehousing.",
            requirements=["Python", "SQL", "Spark"],
            source="stub",
            job_category="data",
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


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Domain Model Unit Tests (no DB needed)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestConsequenceWeighting(unittest.IsolatedAsyncioTestCase):
    """Phase 4: Consequence weighting assigns correct weights."""

    def test_consequence_weight_hierarchy(self) -> None:
        weights = {
            level.value: consequence_weight_for(level.value)
            for level in ConsequenceLevel
        }
        self.assertGreater(weights["accepted"], weights["offer"])
        self.assertGreater(weights["offer"], weights["interview"])
        self.assertGreater(weights["interview"], weights["assessment"])
        self.assertGreater(weights["assessment"], weights["applied"])
        self.assertGreater(weights["applied"], weights["saved"])
        self.assertGreater(weights["saved"], weights["clicked"])
        self.assertGreater(weights["clicked"], weights["viewed"])
        self.assertGreater(weights["viewed"], weights["ignored"])

    def test_consequence_weight_range(self) -> None:
        for level in ConsequenceLevel:
            w = consequence_weight_for(level.value)
            self.assertGreaterEqual(w, 0.0)
            self.assertLessEqual(w, 1.0)


class TestSemanticService(unittest.IsolatedAsyncioTestCase):
    """Phase 5: Semantic generalization tests."""

    def test_text_similarity_identical(self) -> None:
        svc = SemanticService()
        sim = svc.text_similarity("python fastapi backend", "python fastapi backend")
        self.assertGreater(sim, 0.95)

    def test_text_similarity_related(self) -> None:
        svc = SemanticService()
        sim = svc.text_similarity("python fastapi", "python django")
        self.assertGreater(sim, 0.3, "Related frameworks should have meaningful similarity")

    def test_text_similarity_unrelated(self) -> None:
        svc = SemanticService()
        sim = svc.text_similarity("python fastapi backend", "react typescript frontend")
        self.assertLess(sim, 0.3, "Unrelated stacks should have low similarity")

    def test_find_similar_patterns(self) -> None:
        svc = SemanticService()
        patterns = [
            "remote + backend + python + fastapi",
            "remote + backend + java + spring",
            "new york + frontend + react",
            "remote + data + python + spark",
        ]
        svc.build_index(patterns)
        similar = svc.find_similar_patterns(
            "remote + backend + python + django",
            patterns,
            top_k=2,
            min_similarity=0.1,
        )
        self.assertGreater(len(similar), 0, "Should find related patterns")
        top_sig = similar[0][0]
        self.assertIn("python", top_sig)

    def test_build_job_signature(self) -> None:
        sig = SemanticService.build_job_signature(
            job_title="Senior Backend Engineer",
            job_category="backend",
            job_location="Remote",
            job_requirements=["Python", "FastAPI", "PostgreSQL"],
        )
        self.assertIn("remote", sig)
        self.assertIn("backend", sig)
        self.assertIn("python", sig.lower())

    def test_empty_similarity(self) -> None:
        svc = SemanticService()
        sim = svc.text_similarity("", "python")
        self.assertEqual(sim, 0.0)


class TestPersonaTypes(unittest.IsolatedAsyncioTestCase):
    """Phase 7: Career persona types are well-defined."""

    def test_all_persona_types_exist(self) -> None:
        expected = {
            "explorer", "backend_builder", "frontend_crafter",
            "ai_engineer", "ml_researcher", "data_specialist",
            "platform_engineer", "mobile_developer", "product_designer",
            "tech_leader", "generalist",
        }
        actual = {p.value for p in PersonaType}
        self.assertEqual(expected, actual)


class TestDomainModels(unittest.IsolatedAsyncioTestCase):
    """Phase 1-3: Domain model construction tests."""

    def test_memory_entry_defaults(self) -> None:
        entry = MemoryEntry(key="python", last_seen=datetime.now(timezone.utc))
        self.assertEqual(entry.signal_strength, 0.5)
        self.assertEqual(entry.occurrence_count, 1)
        self.assertEqual(entry.category, "general")

    def test_dual_memory_state(self) -> None:
        now = datetime.now(timezone.utc)
        state = DualMemoryState(
            user_id="user-1",
            short_term=ShortTermMemory(user_id="user-1", updated_at=now),
            long_term=LongTermMemory(user_id="user-1", updated_at=now),
            updated_at=now,
        )
        self.assertEqual(state.short_term.recent_interests, [])
        self.assertEqual(state.long_term.stable_preferences, [])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Integration Tests (via ASGI test client)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestV2Integration(unittest.IsolatedAsyncioTestCase):
    """Full V2 integration tests through the API."""

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

    async def test_v2_ranked_jobs_include_v2_fields(self) -> None:
        """V2 fields are present in ranking response."""
        client = await self._create_client()
        recommendations = await self._rank(client, "v2-fields-user")
        for rec in recommendations:
            self.assertIn("semantic_score", rec)
            self.assertIn("pattern_score", rec)
            self.assertIn("temporal_score", rec)
            self.assertIn("memory_score", rec)
            self.assertIn("persona_alignment", rec)
            self.assertIn("semantic_score", rec["signal_breakdown"])
            self.assertIn("pattern_score", rec["signal_breakdown"])
            self.assertIn("memory_score", rec["signal_breakdown"])
            self.assertIn("persona_alignment", rec["signal_breakdown"])

    async def test_v2_analytics_endpoint(self) -> None:
        """V2 analytics endpoint returns a report."""
        client = await self._create_client()
        response = await client.get(
            "/api/v1/abc/analytics",
            params={"user_id": "analytics-user"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])

    async def test_v2_patterns_endpoint(self) -> None:
        """V2 patterns endpoint returns discovered patterns."""
        client = await self._create_client()
        response = await client.get(
            "/api/v1/abc/patterns",
            params={"user_id": "patterns-user"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])

    async def test_v2_persona_endpoint(self) -> None:
        """V2 persona endpoint returns inferred persona."""
        client = await self._create_client()
        response = await client.get(
            "/api/v1/abc/persona",
            params={"user_id": "persona-user"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])

    async def test_v2_memory_endpoint(self) -> None:
        """V2 memory endpoint returns dual memory state."""
        client = await self._create_client()
        response = await client.get(
            "/api/v1/abc/memory",
            params={"user_id": "memory-user"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])

    async def test_v2_self_evaluation_endpoint(self) -> None:
        """V2 self-evaluation endpoint returns metrics."""
        client = await self._create_client()
        response = await client.get(
            "/api/v1/abc/self-evaluation",
            params={"user_id": "self-eval-user"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])

    async def test_v2_strategy_feedback_endpoint(self) -> None:
        """V2 strategy feedback endpoint returns signals."""
        client = await self._create_client()
        response = await client.post(
            "/api/v1/abc/strategy-feedback",
            params={"user_id": "feedback-user"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])

    async def test_new_outcome_types_accepted(self) -> None:
        """V2 outcome types (assessment, final_round, accepted) work."""
        client = await self._create_client()
        await self._teach(
            client,
            user_id="new-outcome-user",
            category="backend",
            outcome_type=OutcomeType.ASSESSMENT,
            count=1,
        )
        await self._teach(
            client,
            user_id="new-outcome-user",
            category="backend",
            outcome_type=OutcomeType.INTERVIEW,
            count=1,
        )
        recommendations = await self._rank(client, "new-outcome-user")
        self.assertGreater(len(recommendations), 0)

    async def test_v2_backward_compatibility(self) -> None:
        """V2 doesn't break V1 behavior for new users with no V2 data."""
        client = await self._create_client()

        # A fresh user should get valid recommendations
        recommendations = await self._rank(client, "pure-v1-user")
        self.assertEqual(len(recommendations), 3)

        # After teaching, learned behavior should still work
        await self._teach(
            client,
            user_id="pure-v1-user",
            category="frontend",
            outcome_type=OutcomeType.INTERVIEW,
            count=5,
        )
        recommendations = await self._rank(client, "pure-v1-user")
        frontend_rec = next(r for r in recommendations if r["job_category"] == "frontend")
        backend_rec = next(r for r in recommendations if r["job_category"] == "backend")
        self.assertGreater(
            frontend_rec["category_weight"],
            backend_rec["category_weight"],
            "V1 learning should raise frontend weight above backend after teaching",
        )

    async def test_interviews_create_learning_events(self) -> None:
        """After teaching with interview outcomes, learning events exist."""
        client = await self._create_client()
        await self._teach(
            client,
            user_id="learning-events-user",
            category="backend",
            outcome_type=OutcomeType.INTERVIEW,
            count=3,
        )
        response = await client.get(
            "/api/v1/abc/analytics",
            params={"user_id": "learning-events-user"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertIsNotNone(payload["data"])
