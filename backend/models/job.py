"""
Job models.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class Job(BaseModel):
    """A single job listing."""

    hunt_id: str | None = None
    job_id: str
    title: str
    company: str
    location: str
    description: str = ""
    requirements: list[str] = Field(default_factory=list)
    salary_range: str | None = None
    url: str | None = None
    source: str = "web_scraper"
    posted_date: str | None = None
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ranking_position: int | None = None
    base_match_score: float | None = None
    final_score: float | None = None
    recommendation_reason: str | None = None
    recommendation_event_id: str | None = None
    job_category: str | None = None
    trust_score: float | None = Field(default=None, ge=0, le=1)
    source_confidence: float | None = Field(default=None, ge=0, le=1)
    legitimacy_probability: float | None = Field(default=None, ge=0, le=1)
    scam_flags: list[str] = Field(default_factory=list)
    duplicate_of: str | None = None


class JobSearchResult(BaseModel):
    """Search results for a hunt."""

    query: str
    location: str = ""
    total_found: int = 0
    jobs: list[Job] = Field(default_factory=list)
