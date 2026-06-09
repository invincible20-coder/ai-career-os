"""
Parser utilities for scraped job payloads.
"""

from __future__ import annotations

import hashlib
from typing import Any

from backend.core.logger import get_logger
from backend.models.job import Job, JobSearchResult

logger = get_logger(__name__)


def parse_raw_jobs(
    raw_jobs: list[dict[str, Any]],
    *,
    query: str,
    location: str,
) -> JobSearchResult:
    """Convert raw dictionaries into validated `Job` instances."""

    jobs: list[Job] = []
    for raw_job in raw_jobs:
        try:
            jobs.append(_parse_single(raw_job))
        except Exception as exc:
            logger.warning(
                "job_parse_skipped",
                extra={
                    "event": "job_parse_skipped",
                    "title": raw_job.get("title", "unknown"),
                    "reason": str(exc),
                },
            )

    return JobSearchResult(
        query=query,
        location=location,
        total_found=len(jobs),
        jobs=jobs,
    )


def _parse_single(raw_job: dict[str, Any]) -> Job:
    title = _clean(raw_job.get("title", "Unknown Title"))
    company = _clean(raw_job.get("company", "Unknown Company"))
    url = _clean(raw_job.get("url", ""))

    seed = f"{title.lower()}::{company.lower()}::{url.lower()}"
    job_id = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]

    requirements = raw_job.get("requirements", [])
    if isinstance(requirements, str):
        requirements = [item.strip() for item in requirements.split(",") if item.strip()]

    return Job(
        job_id=job_id,
        title=title,
        company=company,
        location=_clean(raw_job.get("location", "Remote")),
        description=_clean(raw_job.get("description", "")),
        requirements=requirements,
        salary_range=raw_job.get("salary_range"),
        url=raw_job.get("url"),
        source=raw_job.get("source", "unknown"),
        posted_date=raw_job.get("posted_date"),
        trust_score=raw_job.get("trust_score"),
        source_confidence=raw_job.get("source_confidence"),
        legitimacy_probability=raw_job.get("legitimacy_probability"),
        scam_flags=raw_job.get("scam_flags") or [],
        duplicate_of=raw_job.get("duplicate_of"),
    )


def _clean(value: Any) -> str:
    return " ".join(str(value).split())
