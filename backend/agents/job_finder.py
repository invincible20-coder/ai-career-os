"""
Job finder agent.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.core.logger import get_logger
from backend.models.job import JobSearchResult
from backend.tools.parser import parse_raw_jobs
from backend.tools.scraper import scrape_jobs

logger = get_logger(__name__)


@dataclass(slots=True)
class JobFinderAgent:
    """Search for jobs using scraper and parser tools."""

    default_country: str
    max_jobs_per_search: int

    async def search(
        self,
        *,
        query: str,
        location: str | None = None,
        max_results: int | None = None,
    ) -> JobSearchResult:
        resolved_location = location or self.default_country
        resolved_max_results = max_results or self.max_jobs_per_search

        logger.info(
            "job_search_started",
            extra={
                "event": "job_search_started",
                "query": query,
                "location": resolved_location,
                "max_results": resolved_max_results,
            },
        )

        raw_jobs = await scrape_jobs(
            query=query,
            location=resolved_location,
            max_results=resolved_max_results,
        )
        result = parse_raw_jobs(raw_jobs, query=query, location=resolved_location)

        logger.info(
            "job_search_completed",
            extra={
                "event": "job_search_completed",
                "query": query,
                "location": resolved_location,
                "total_found": result.total_found,
            },
        )
        return result
