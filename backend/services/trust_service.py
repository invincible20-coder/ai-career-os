"""
Job trust scoring, scam detection, and semantic deduplication.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any


_SUSPICIOUS_TERMS = {
    "registration fee": "asks_for_registration_fee",
    "processing fee": "asks_for_processing_fee",
    "telegram": "telegram_recruiter",
    "whatsapp only": "whatsapp_only",
    "guaranteed job": "guaranteed_job_claim",
    "earn money fast": "get_rich_quick_language",
    "no interview": "no_interview_claim",
    "urgent hiring pay first": "pay_first_language",
}
_SOURCE_CONFIDENCE = {
    "company_site": 0.95,
    "linkedin": 0.86,
    "indeed": 0.82,
    "remoteok": 0.78,
    "startup_board": 0.74,
    "internship_board": 0.70,
    "synthetic": 0.62,
    "unknown": 0.45,
}


@dataclass(slots=True)
class JobTrustService:
    """Deterministic trust intelligence for scraped job listings."""

    def enrich_jobs(self, jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Apply trust metadata and semantic deduplication."""

        enriched = [self.enrich_job(job) for job in jobs]
        return self.semantic_dedupe(enriched)

    def enrich_job(self, job: dict[str, Any]) -> dict[str, Any]:
        text = self._job_text(job)
        flags = self._scam_flags(text, job.get("url"))
        source = str(job.get("source", "unknown")).lower()
        source_confidence = _SOURCE_CONFIDENCE.get(source, _SOURCE_CONFIDENCE["unknown"])
        completeness = self._completeness(job)
        salary_score = self._salary_legitimacy(str(job.get("salary_range") or ""))
        link_score = 0.35 if self._has_malicious_link(job.get("url")) else 1.0
        penalty = min(0.75, len(flags) * 0.16)
        legitimacy = max(
            0.0,
            min(
                1.0,
                completeness * 0.34
                + source_confidence * 0.28
                + salary_score * 0.18
                + link_score * 0.20
                - penalty,
            ),
        )
        trust_score = round((source_confidence * 0.45 + legitimacy * 0.55), 4)
        return {
            **job,
            "trust_score": trust_score,
            "source_confidence": round(source_confidence, 4),
            "legitimacy_probability": round(legitimacy, 4),
            "scam_flags": flags,
        }

    def semantic_dedupe(self, jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Drop cloned listings using normalized title/company/requirements overlap."""

        kept: list[dict[str, Any]] = []
        fingerprints: dict[str, str] = {}
        for job in sorted(jobs, key=lambda item: item.get("trust_score", 0), reverse=True):
            signature = self._semantic_signature(job)
            duplicate_of = fingerprints.get(signature)
            if duplicate_of:
                kept.append({**job, "duplicate_of": duplicate_of})
                continue
            stable_id = hashlib.sha256(
                f"{job.get('title')}::{job.get('company')}::{job.get('url')}".encode("utf-8")
            ).hexdigest()[:16]
            fingerprints[signature] = stable_id
            kept.append({**job, "duplicate_of": None})
        return [job for job in kept if job.get("duplicate_of") is None]

    @staticmethod
    def _job_text(job: dict[str, Any]) -> str:
        return " ".join(
            [
                str(job.get("title", "")),
                str(job.get("company", "")),
                str(job.get("description", "")),
                " ".join(str(item) for item in job.get("requirements", []) or []),
                str(job.get("salary_range", "")),
                str(job.get("url", "")),
            ]
        ).lower()

    @staticmethod
    def _scam_flags(text: str, url: Any) -> list[str]:
        flags = [flag for term, flag in _SUSPICIOUS_TERMS.items() if term in text]
        if JobTrustService._has_malicious_link(url):
            flags.append("suspicious_link")
        if re.search(r"\b\d{7,}\s*-\s*\d{8,}\b", text):
            flags.append("unrealistic_salary_range")
        return sorted(set(flags))

    @staticmethod
    def _has_malicious_link(url: Any) -> bool:
        value = str(url or "").lower()
        return bool(value and not value.startswith(("https://", "http://localhost", "http://127.")))

    @staticmethod
    def _completeness(job: dict[str, Any]) -> float:
        fields = ["title", "company", "location", "description", "requirements", "url"]
        present = sum(bool(job.get(field)) for field in fields)
        description = str(job.get("description", ""))
        description_bonus = 0.15 if len(description.split()) >= 25 else 0.0
        return min(1.0, present / len(fields) + description_bonus)

    @staticmethod
    def _salary_legitimacy(salary_range: str) -> float:
        if not salary_range:
            return 0.65
        numbers = [float(value.replace(",", "")) for value in re.findall(r"\d[\d,]*", salary_range)]
        if len(numbers) >= 2 and max(numbers) > min(numbers) * 8:
            return 0.35
        return 0.85

    @staticmethod
    def _semantic_signature(job: dict[str, Any]) -> str:
        tokens = {
            token
            for token in re.findall(
                r"[a-z0-9]+",
                " ".join(
                    [
                        str(job.get("title", "")),
                        str(job.get("company", "")),
                        " ".join(str(item) for item in job.get("requirements", []) or []),
                    ]
                ).lower(),
            )
            if len(token) > 2
        }
        return "|".join(sorted(tokens))
