"""
Deterministic local LLM-compatible wrapper used by LLM-powered agents.
"""

from __future__ import annotations

import os
import re
from time import perf_counter
from typing import Any, Protocol

from backend.core.logger import get_logger

logger = get_logger(__name__)


class SupportsJsonCompletion(Protocol):
    """Protocol for JSON-capable LLM clients."""

    async def complete_json(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Return a parsed JSON response."""


class OpenAIJSONClient:
    """Drop-in, offline JSON completion client with OpenAI-compatible shape."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        default_temperature: float,
        default_max_tokens: int,
        timeout_seconds: float,
    ) -> None:
        self._model = model
        self._default_temperature = default_temperature
        self._default_max_tokens = default_max_tokens
        self._timeout_seconds = timeout_seconds
        self._use_mock_llm = os.getenv("USE_MOCK_LLM", "true").lower() == "true"

        if not self._use_mock_llm:
            logger.warning(
                "mock_llm_forced",
                extra={
                    "event": "mock_llm_forced",
                    "reason": "External LLM calls are disabled in this offline build",
                },
            )

    async def complete_json(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        logger.debug(
            "llm_request",
            extra={
                "event": "llm_request",
                "model": self._model,
                "provider": "local_mock",
                "messages": len(messages),
            },
        )

        started_at = perf_counter()
        response = self._generate_response(messages)

        logger.debug(
            "llm_response",
            extra={
                "event": "llm_response",
                "model": self._model,
                "provider": "local_mock",
                "latency_ms": round((perf_counter() - started_at) * 1000),
            },
        )
        return response

    def _generate_response(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        prompt = "\n".join(message.get("content", "") for message in messages)
        prompt_lower = prompt.lower()
        user_content = self._last_user_message(messages)

        if "planning agent" in prompt_lower or "execution plan" in prompt_lower:
            return self._planning_response(user_content)
        if "resume writer" in prompt_lower:
            return self._resume_response(user_content)
        if "cover letter writer" in prompt_lower:
            return self._cover_letter_response(user_content)
        if "career recommendation agent" in prompt_lower:
            return self._career_response(user_content)

        return {"content": "Generated deterministic mock response"}

    @staticmethod
    def _last_user_message(messages: list[dict[str, str]]) -> str:
        for message in reversed(messages):
            if message.get("role") == "user":
                return message.get("content", "")
        return messages[-1].get("content", "") if messages else ""

    @staticmethod
    def _field(content: str, name: str) -> str:
        match = re.search(rf"^{re.escape(name)}:\s*(.+)$", content, flags=re.MULTILINE)
        return match.group(1).strip() if match else ""

    @staticmethod
    def _clean_goal(raw_goal: str) -> str:
        goal = raw_goal.strip()
        if ":" in goal:
            goal = goal.split(":", 1)[1].strip()
        return goal or "Find suitable software engineering roles"

    @staticmethod
    def _search_query(goal: str) -> str:
        cleaned = re.sub(r"\s+", " ", goal).strip()
        cleaned = re.sub(r"^(find|get|search for|apply to)\s+", "", cleaned, flags=re.I)
        return cleaned[:120] or "software engineer"

    def _planning_response(self, user_content: str) -> dict[str, Any]:
        goal = self._clean_goal(user_content)
        query = self._search_query(goal)
        location = "Remote" if "remote" in goal.lower() else "India"

        return {
            "goal": goal,
            "summary": f"Search for strong-fit {query} opportunities and prepare tailored applications.",
            "steps": [
                {
                    "step_number": 1,
                    "step_type": "plan",
                    "description": "Confirm the job hunt strategy and execution order.",
                    "parameters": {},
                },
                {
                    "step_number": 2,
                    "step_type": "search",
                    "description": "Search for matching jobs using the refined goal.",
                    "parameters": {
                        "query": query,
                        "location": location,
                        "max_results": 10,
                    },
                },
                {
                    "step_number": 3,
                    "step_type": "apply",
                    "description": "Tailor resume and cover letter and prepare applications.",
                    "parameters": {},
                },
                {
                    "step_number": 4,
                    "step_type": "track",
                    "description": "Track prepared applications and outcomes.",
                    "parameters": {},
                },
            ],
        }

    def _resume_response(self, user_content: str) -> dict[str, Any]:
        title = self._field(user_content, "Title") or "the target role"
        requirements = self._field(user_content, "Requirements")
        skills = requirements if requirements and requirements != "Not provided" else "Python, APIs, Databases"
        content = "Generated resume tailored for the job using keywords"

        return {
            "content": content,
            "summary": (
                f"Technical candidate aligned with {title}, focused on building reliable systems, "
                "clean APIs, and maintainable backend services."
            ),
            "skills_section": skills,
            "experience_section": (
                "- Built backend services with clear APIs and database-backed workflows.\n"
                "- Improved reliability through validation, logging, and structured error handling.\n"
                "- Collaborated across product requirements to deliver job-relevant features."
            ),
        }

    def _cover_letter_response(self, user_content: str) -> dict[str, Any]:
        title = self._field(user_content, "Title") or "the role"
        company = self._field(user_content, "Company") or "your team"
        content = "Generated cover letter for the job role"

        return {
            "content": content,
            "greeting": "Dear Hiring Manager,",
            "body": (
                f"I am excited to apply for {title} at {company}. My background aligns with "
                "building practical, reliable software systems and adapting quickly to product needs.\n\n"
                "I can contribute by creating maintainable backend workflows, clear API contracts, "
                "and user-focused automation that supports measurable outcomes.\n\n"
                "I would welcome the opportunity to bring this execution-focused approach to your team."
            ),
            "closing": "Sincerely,",
        }

    def _career_response(self, user_content: str) -> dict[str, Any]:
        profile = user_content.lower()
        if any(keyword in profile for keyword in ("python", "api", "backend", "systems")):
            roles = [
                {
                    "role": "Backend Developer",
                    "reason": "Based on Python, API development, and interest in building systems.",
                    "required_skills": ["Python", "FastAPI", "Databases"],
                },
                {
                    "role": "API Engineer",
                    "reason": "Matches API-focused skills and backend service design interests.",
                    "required_skills": ["REST APIs", "HTTP", "Testing"],
                },
                {
                    "role": "Software Engineer",
                    "reason": "Broad fit for technical problem solving and software delivery.",
                    "required_skills": ["Programming", "System Design", "Version Control"],
                },
            ]
        else:
            roles = [
                {
                    "role": "Software Engineer",
                    "reason": "Matches a general technical profile with room to specialize.",
                    "required_skills": ["Programming", "Problem Solving", "Git"],
                },
                {
                    "role": "Product Analyst",
                    "reason": "Fits exploratory interests and structured decision making.",
                    "required_skills": ["Analytics", "SQL", "Communication"],
                },
                {
                    "role": "Technical Support Engineer",
                    "reason": "Good bridge role for learning systems while solving user problems.",
                    "required_skills": ["Troubleshooting", "Documentation", "Customer Communication"],
                },
            ]

        return {"recommended_roles": roles}
