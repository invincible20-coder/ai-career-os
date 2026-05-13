"""
Application assembly agent.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha1

from backend.models.application import Application, ApplicationStatus, CoverLetter, ResumeContent
from backend.models.behavior import ApplicationOutcomeStatus
from backend.models.job import Job


@dataclass(slots=True)
class ApplicationAgent:
    """Assemble a complete application payload."""

    async def prepare(
        self,
        hunt_id: str,
        job: Job,
        resume: ResumeContent,
        cover_letter: CoverLetter,
        resume_version: str = "standard-v1",
        is_referral: bool = False,
    ) -> Application:
        application_id = f"APP-{sha1(f'{hunt_id}:{job.job_id}'.encode('utf-8')).hexdigest()[:12].upper()}"
        created_at = datetime.now(timezone.utc)
        return Application(
            hunt_id=hunt_id,
            application_id=application_id,
            job_id=job.job_id,
            role=job.title,
            job_title=job.title,
            company=job.company,
            platform=job.source,
            resume_version=resume_version,
            timestamp_applied=created_at,
            application_status=ApplicationOutcomeStatus.NO_RESPONSE,
            is_referral=is_referral,
            resume=resume,
            cover_letter=cover_letter,
            status=ApplicationStatus.PREPARED,
            created_at=created_at,
            notes=f"Application prepared for {job.title} at {job.company}",
        )
