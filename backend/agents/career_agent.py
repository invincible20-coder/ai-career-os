"""
Career recommendation agent.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import ValidationError

from backend.core.llm import SupportsJsonCompletion
from backend.core.logger import get_logger
from backend.models.career import CareerRecommendation, RoleSuggestion, UserProfile
from backend.models.errors import ErrorDetail
from backend.services.exceptions import BadRequestError, PipelineExecutionError

logger = get_logger(__name__)

SYSTEM_PROMPT = """\
You are a career recommendation agent for a job hunting platform.

Given a partial user profile, recommend the most suitable job roles.
Return ONLY valid JSON in this schema:
{
  "recommended_roles": [
    {
      "role": "Backend Developer",
      "reason": "Based on Python and API development skills",
      "required_skills": ["Python", "FastAPI", "Databases"]
    }
  ]
}

Rules:
- Recommend between 3 and 5 realistic roles.
- Base each role on the supplied profile only.
- Keep reasons concise and specific.
- `required_skills` must be practical skills for that role.
- Do not return prose outside the JSON object.
"""


@dataclass(slots=True)
class CareerAgent:
    """Analyze a user profile and return role recommendations."""

    llm_client: SupportsJsonCompletion

    async def recommend(self, profile: UserProfile) -> CareerRecommendation:
        if not profile.has_signal():
            raise BadRequestError(
                "Career recommendations require at least one profile field",
                errors=[
                    ErrorDetail(
                        code="missing_profile_signal",
                        message="Provide skills, education, interests, or experience",
                        step="career_recommendation",
                    )
                ],
            )

        logger.info(
            "career_recommendation_requested",
            extra={"event": "career_recommendation_requested"},
        )

        try:
            data = await self.llm_client.complete_json(
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": profile.to_prompt_block()},
                ],
                temperature=0.3,
            )
            recommendation = CareerRecommendation(
                recommended_roles=[
                    RoleSuggestion(**role)
                    for role in data.get("recommended_roles", [])
                ]
            )
        except (TypeError, ValueError, ValidationError) as exc:
            raise PipelineExecutionError(
                "Career agent returned malformed output",
                errors=[
                    ErrorDetail(
                        code="invalid_career_payload",
                        message="Career recommendation output could not be parsed",
                        step="career_recommendation",
                        details={"reason": str(exc)},
                    )
                ],
            ) from exc
        if not recommendation.recommended_roles:
            raise PipelineExecutionError(
                "Career agent returned no recommendations",
                errors=[
                    ErrorDetail(
                        code="empty_career_recommendations",
                        message="Career recommendation output did not contain any roles",
                        step="career_recommendation",
                    )
                ],
            )
        return recommendation
