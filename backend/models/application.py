"""
Application and tracker models.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from backend.models.behavior import ApplicationOutcomeStatus


class ApplicationStatus(str, Enum):
    PREPARED = "prepared"
    SUBMITTED = "submitted"
    FAILED = "failed"


class ResumeContent(BaseModel):
    """Tailored resume content."""

    job_id: str
    summary: str
    skills_section: str
    experience_section: str
    full_text: str = ""


class CoverLetter(BaseModel):
    """Tailored cover letter content."""

    job_id: str
    greeting: str = "Dear Hiring Manager,"
    body: str
    closing: str = "Sincerely,"
    full_text: str = ""


class Application(BaseModel):
    """Prepared application payload."""

    hunt_id: str
    application_id: str
    job_id: str
    role: str
    job_title: str
    company: str
    platform: str = "unknown"
    resume_version: str = "standard-v1"
    timestamp_applied: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    application_status: ApplicationOutcomeStatus = ApplicationOutcomeStatus.NO_RESPONSE
    is_referral: bool = False
    resume: ResumeContent
    cover_letter: CoverLetter
    status: ApplicationStatus = ApplicationStatus.PREPARED
    submitted_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notes: str = ""


class TrackerEntry(BaseModel):
    """Tracker projection derived from applications."""

    hunt_id: str
    application_id: str
    job_id: str
    job_title: str
    company: str
    platform: str = "unknown"
    resume_version: str = "standard-v1"
    application_status: ApplicationOutcomeStatus = ApplicationOutcomeStatus.NO_RESPONSE
    is_referral: bool = False
    status: ApplicationStatus
    created_at: datetime
    submitted_at: datetime | None = None
