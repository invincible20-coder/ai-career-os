"""
Tracker projection agent.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.models.application import Application, TrackerEntry


@dataclass(slots=True)
class TrackingAgent:
    """Build tracker entries from prepared applications."""

    async def build_entries(
        self,
        hunt_id: str,
        applications: list[Application],
    ) -> list[TrackerEntry]:
        return [
            TrackerEntry(
                hunt_id=hunt_id,
                application_id=application.application_id,
                job_id=application.job_id,
                job_title=application.job_title,
                company=application.company,
                platform=application.platform,
                resume_version=application.resume_version,
                application_status=application.application_status,
                is_referral=application.is_referral,
                status=application.status,
                created_at=application.created_at,
                submitted_at=application.submitted_at,
            )
            for application in applications
        ]
