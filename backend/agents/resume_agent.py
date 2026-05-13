"""
Resume generation agent.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import ValidationError

from backend.core.llm import SupportsJsonCompletion
from backend.models.errors import ErrorDetail
from backend.models.application import ResumeContent
from backend.models.job import Job
from backend.services.exceptions import PipelineExecutionError

SYSTEM_PROMPT = """\
You are an expert resume writer for technical candidates.

Return ONLY valid JSON:
{
  "summary": "<2-3 sentence professional summary>",
  "skills_section": "<comma-separated job-relevant skills>",
  "experience_section": "<3 concise bullets of relevant experience>"
}

Rules:
- Tailor the response to the role requirements.
- Do not fabricate specific employers, dates, or certifications.
- Keep the tone professional and concise.
"""


@dataclass(slots=True)
class ResumeAgent:
    """Generate tailored resume content."""

    llm_client: SupportsJsonCompletion

    async def generate(self, job: Job) -> ResumeContent:
        try:
            data = await self.llm_client.complete_json(
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"Title: {job.title}\n"
                            f"Company: {job.company}\n"
                            f"Location: {job.location}\n"
                            f"Description: {job.description}\n"
                            f"Requirements: {', '.join(job.requirements)}\n"
                        ),
                    },
                ],
                temperature=0.5,
            )

            summary = data.get("summary", "")
            skills_section = data.get("skills_section", "")
            experience_section = data.get("experience_section", "")

            return ResumeContent(
                job_id=job.job_id,
                summary=summary,
                skills_section=skills_section,
                experience_section=experience_section,
                full_text=(
                    f"PROFESSIONAL SUMMARY\n{summary}\n\n"
                    f"KEY SKILLS\n{skills_section}\n\n"
                    f"RELEVANT EXPERIENCE\n{experience_section}"
                ),
            )
        except (TypeError, ValueError, ValidationError) as exc:
            raise PipelineExecutionError(
                "Resume agent returned malformed output",
                errors=[
                    ErrorDetail(
                        code="invalid_resume_payload",
                        message="Resume generation output could not be parsed",
                        step="apply",
                        details={"job_id": job.job_id, "reason": str(exc)},
                    )
                ],
            ) from exc
