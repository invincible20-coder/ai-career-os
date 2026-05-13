"""
Planner agent that creates the high-level hunt workflow.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import ValidationError

from backend.core.llm import SupportsJsonCompletion
from backend.core.logger import get_logger
from backend.models.errors import ErrorDetail
from backend.models.plan import ExecutionPlan, PlanStep
from backend.services.exceptions import PlanValidationError

logger = get_logger(__name__)

SYSTEM_PROMPT = """\
You are the planning agent for an autonomous job hunting backend.

Return ONLY valid JSON in this schema:
{
  "goal": "<original goal>",
  "summary": "<short strategy summary>",
  "steps": [
    {
      "step_number": 1,
      "step_type": "plan",
      "description": "<confirm the strategy>",
      "parameters": {}
    },
    {
      "step_number": 2,
      "step_type": "search",
      "description": "<search for matching jobs>",
      "parameters": {
        "query": "<search query>",
        "location": "<preferred location or Remote>",
        "max_results": 10
      }
    },
    {
      "step_number": 3,
      "step_type": "apply",
      "description": "<tailor resume and cover letter and prepare applications>",
      "parameters": {}
    },
    {
      "step_number": 4,
      "step_type": "track",
      "description": "<track prepared applications>",
      "parameters": {}
    }
  ]
}

Rules:
- Return exactly four steps.
- The step order must be: plan, search, apply, track.
- Do not invent extra steps.
- Keep the search query concise and role-specific.
"""


@dataclass(slots=True)
class PlannerAgent:
    """Generate execution plans using the LLM."""

    llm_client: SupportsJsonCompletion

    async def create_plan(self, goal: str) -> ExecutionPlan:
        logger.info(
            "planner_invoked",
            extra={"event": "planner_invoked", "goal": goal},
        )

        try:
            data = await self.llm_client.complete_json(
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"My goal is: {goal}"},
                ],
                temperature=0.2,
            )
            return ExecutionPlan(
                goal=data.get("goal", goal),
                summary=data.get("summary", ""),
                steps=[PlanStep(**step) for step in data.get("steps", [])],
            )
        except (TypeError, ValueError, ValidationError) as exc:
            raise PlanValidationError(
                "Planner returned malformed output",
                errors=[
                    ErrorDetail(
                        code="invalid_plan_payload",
                        message="Planner output could not be parsed into a valid workflow",
                        step="plan",
                        details={"reason": str(exc)},
                    )
                ],
            ) from exc
