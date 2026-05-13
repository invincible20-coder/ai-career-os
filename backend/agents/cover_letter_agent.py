"""
Cover letter generation agent.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import ValidationError

from backend.core.llm import SupportsJsonCompletion
from backend.models.errors import ErrorDetail
from backend.models.application import CoverLetter
from backend.models.job import Job
from backend.services.exceptions import PipelineExecutionError

SYSTEM_PROMPT = """\
You are an expert cover letter writer for technical roles.

Return ONLY valid JSON:
{
  "greeting": "Dear Hiring Manager,",
  "body": "<3 short paragraphs tailored to the job>",
  "closing": "Sincerely,"
}

Rules:
- Reference the role and company directly.
- Keep the response under 350 words.
- Do not fabricate experience.
"""


@dataclass(slots=True)
class CoverLetterAgent:
    """Generate tailored cover letters."""

    llm_client: SupportsJsonCompletion

    async def generate(self, job: Job) -> CoverLetter:
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
                temperature=0.6,
            )

            greeting = data.get("greeting", "Dear Hiring Manager,")
            body = data.get("body", "")
            closing = data.get("closing", "Sincerely,")

            return CoverLetter(
                job_id=job.job_id,
                greeting=greeting,
                body=body,
                closing=closing,
                full_text=f"{greeting}\n\n{body}\n\n{closing}",
            )
        except (TypeError, ValueError, ValidationError) as exc:
            raise PipelineExecutionError(
                "Cover letter agent returned malformed output",
                errors=[
                    ErrorDetail(
                        code="invalid_cover_letter_payload",
                        message="Cover letter generation output could not be parsed",
                        step="apply",
                        details={"job_id": job.job_id, "reason": str(exc)},
                    )
                ],
            ) from exc
