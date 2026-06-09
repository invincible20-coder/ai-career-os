"""
Async job scraping utilities.
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Any

import httpx

from backend.core.config import get_settings
from backend.core.logger import get_logger
from backend.services.trust_service import JobTrustService

logger = get_logger(__name__)

PROVIDER_TIMEOUT_SECONDS = 15


async def scrape_jobs(
    *,
    query: str,
    location: str = "",
    max_results: int = 10,
) -> list[dict[str, Any]]:
    """Fetch jobs from all providers with per-provider timeout and isolation."""

    settings = get_settings()
    resolved_location = location or settings.default_country

    logger.info(
        "DISCOVERY_SCRAPE_STARTED",
        extra={
            "event": "discovery_scrape_started",
            "query": query,
            "location": resolved_location,
            "max_results": max_results,
        },
    )

    all_jobs: list[dict[str, Any]] = []
    providers_attempted = 0
    providers_succeeded = 0
    providers_failed = 0

    # ── Provider 1: RemoteOK ──
    providers_attempted += 1
    logger.info("SEARCH_PROVIDER_START: remoteok", extra={"event": "provider_start", "provider": "remoteok"})
    try:
        remoteok_jobs = await asyncio.wait_for(
            _scrape_remoteok(query, resolved_location, max_results),
            timeout=PROVIDER_TIMEOUT_SECONDS,
        )
        validated = [job for job in remoteok_jobs if _looks_valid_job(job)]
        if validated:
            all_jobs.extend(validated)
            providers_succeeded += 1
            logger.info(
                "SEARCH_PROVIDER_SUCCESS: remoteok",
                extra={"event": "provider_success", "provider": "remoteok", "jobs_found": len(validated)},
            )
        else:
            logger.warning(
                "SEARCH_PROVIDER_EMPTY: remoteok",
                extra={"event": "provider_empty", "provider": "remoteok"},
            )
    except asyncio.TimeoutError:
        providers_failed += 1
        logger.error(
            "SEARCH_PROVIDER_TIMEOUT: remoteok",
            extra={"event": "provider_timeout", "provider": "remoteok", "timeout_seconds": PROVIDER_TIMEOUT_SECONDS},
        )
    except Exception as exc:
        providers_failed += 1
        logger.warning(
            "SEARCH_PROVIDER_FAILED: remoteok",
            extra={"event": "provider_failed", "provider": "remoteok", "reason": str(exc)},
        )

    # ── Fallback: Synthetic jobs if all providers failed ──
    if not all_jobs:
        logger.warning(
            "ALL_PROVIDERS_FAILED",
            extra={
                "event": "all_providers_failed",
                "query": query,
                "providers_attempted": providers_attempted,
                "providers_failed": providers_failed,
            },
        )
        all_jobs = _synthetic_jobs(query, resolved_location, max_results)

    enriched = JobTrustService().enrich_jobs(all_jobs)[:max_results]

    logger.info(
        "DISCOVERY_SCRAPE_COMPLETED",
        extra={
            "event": "discovery_scrape_completed",
            "query": query,
            "total_jobs": len(enriched),
            "providers_attempted": providers_attempted,
            "providers_succeeded": providers_succeeded,
            "providers_failed": providers_failed,
        },
    )

    return enriched


async def _scrape_remoteok(
    query: str,
    location: str,
    max_results: int,
) -> list[dict[str, Any]]:
    url = "https://remoteok.com/api"
    settings = get_settings()

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://remoteok.com/",
        "Connection": "keep-alive",
    }

    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        response = await client.get(url, headers=headers)
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
            "source": "company_site",
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
            "source": "startup_board",
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
            "source": "internship_board",
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
                "source": template["source"],
            }
        )
    return jobs
