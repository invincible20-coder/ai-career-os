"""
Async job scraping utilities.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

import httpx

from backend.core.config import get_settings
from backend.core.logger import get_logger

logger = get_logger(__name__)


async def scrape_jobs(
    *,
    query: str,
    location: str = "",
    max_results: int = 10,
) -> list[dict[str, Any]]:
    """Fetch jobs from RemoteOK with a deterministic fallback."""

    settings = get_settings()
    resolved_location = location or settings.default_country

    try:
        live_jobs = await _scrape_remoteok(query, resolved_location, max_results)
        validated_jobs = [job for job in live_jobs if _looks_valid_job(job)]
        if validated_jobs:
            return validated_jobs[:max_results]
        raise ValueError("Scraper returned no valid job payloads")
    except Exception as exc:
        logger.warning(
            "live_scrape_failed",
            extra={
                "event": "live_scrape_failed",
                "query": query,
                "location": resolved_location,
                "reason": str(exc),
            },
        )
        return _synthetic_jobs(query, resolved_location, max_results)


async def _scrape_remoteok(
    query: str,
    location: str,
    max_results: int,
) -> list[dict[str, Any]]:
    url = "https://remoteok.com/api"
    settings = get_settings()

    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        response = await client.get(url, headers={"User-Agent": "JobHuntAgent/2.0"})
        response.raise_for_status()

    data = response.json()
    listings = data[1:] if len(data) > 1 else []
    query_terms = query.lower().split()
    matched: list[dict[str, Any]] = []

    for item in listings:
        searchable = " ".join(
            [
                str(item.get("position", "")),
                str(item.get("company", "")),
                str(item.get("description", "")),
                " ".join(item.get("tags", [])),
            ]
        ).lower()
        if any(term in searchable for term in query_terms):
            matched.append(
                {
                    "title": item.get("position", ""),
                    "company": item.get("company", ""),
                    "location": item.get("location", location),
                    "description": str(item.get("description", ""))[:1500],
                    "requirements": item.get("tags", [])[:10],
                    "url": item.get("url", ""),
                    "salary_range": item.get("salary"),
                    "posted_date": item.get("date"),
                    "source": "remoteok",
                }
            )
        if len(matched) >= max_results:
            break

    if not matched:
        raise ValueError("No matching jobs found from RemoteOK")

    return matched


def _looks_valid_job(raw_job: dict[str, Any]) -> bool:
    return bool(
        str(raw_job.get("title", "")).strip()
        and str(raw_job.get("company", "")).strip()
        and str(raw_job.get("description", "")).strip()
    )


def _synthetic_jobs(query: str, location: str, max_results: int) -> list[dict[str, Any]]:
    templates = [
        {
            "title": f"Senior {query} Engineer",
            "company": "TechCorp Solutions",
            "description": (
                f"We are hiring a Senior {query} Engineer to build scalable backend services, "
                "drive system design, and mentor engineers across the platform team."
            ),
            "requirements": ["Python", "FastAPI", "PostgreSQL", "Docker"],
            "salary_range": "₹18,00,000 - ₹30,00,000",
        },
        {
            "title": f"{query} Developer",
            "company": "InnovateTech Pvt Ltd",
            "description": (
                f"Join our engineering team as a {query} Developer working on APIs, CI/CD, "
                "and internal platform tooling."
            ),
            "requirements": ["Python", "REST APIs", "AWS", "Git"],
            "salary_range": "₹12,00,000 - ₹22,00,000",
        },
        {
            "title": f"{query} Platform Engineer",
            "company": "DataScale Analytics",
            "description": (
                f"Build and operate data-intensive services as a {query} Platform Engineer "
                "with strong ownership across reliability and automation."
            ),
            "requirements": ["Python", "Redis", "Terraform", "System Design"],
            "salary_range": "₹20,00,000 - ₹35,00,000",
        },
    ]

    jobs: list[dict[str, Any]] = []
    for index in range(min(max_results, len(templates))):
        template = templates[index % len(templates)]
        job_hash = hashlib.md5(f"{query}:{location}:{index}".encode("utf-8")).hexdigest()[:10]
        jobs.append(
            {
                "title": template["title"],
                "company": template["company"],
                "location": location,
                "description": template["description"],
                "requirements": template["requirements"],
                "salary_range": template["salary_range"],
                "url": f"https://jobs.example.com/{job_hash}",
                "posted_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "source": "synthetic",
            }
        )
    return jobs
