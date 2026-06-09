"""
Deterministic resume fingerprinting plus confidence-aware outcome correlation.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from statistics import fmean, pstdev

from backend.models.abc import OutcomeType
from backend.models.application import Application
from backend.models.resume_intelligence import (
    ATSBreakdown,
    FeatureCorrelation,
    ResumeIntelligenceReport,
    ResumeOptimizationPrediction,
    ResumeEffectivenessEstimate,
    ResumeFeatures,
    ResumeFingerprint,
    ResumeSemanticProfile,
    ResumeVersionComparison,
    ResumeWeakness,
    ResumeCorrelationProfile,
)
from backend.storage.records import ApplicationRecord, BehaviorEventRecord, OutcomeRecord, utc_now
from backend.storage.repository import HuntRepository


_TECHNICAL_KEYWORDS = {
    "python",
    "java",
    "api",
    "fastapi",
    "django",
    "flask",
    "postgres",
    "sql",
    "redis",
    "docker",
    "kubernetes",
    "react",
    "typescript",
    "analytics",
    "machine learning",
    "etl",
}
_BACKEND_KEYWORDS = {"backend", "api", "python", "fastapi", "django", "flask", "postgres", "redis"}
_FRONTEND_KEYWORDS = {"frontend", "react", "javascript", "typescript", "css", "ui", "web"}
_DATA_KEYWORDS = {"data", "analytics", "sql", "pandas", "etl", "machine learning", "ml"}
_ACTION_VERBS = {
    "built",
    "designed",
    "developed",
    "implemented",
    "improved",
    "optimized",
    "led",
    "launched",
    "reduced",
    "increased",
    "automated",
    "created",
}
_PROJECT_COMPLEXITY_TERMS = {
    "distributed",
    "scalable",
    "microservices",
    "architecture",
    "pipeline",
    "latency",
    "throughput",
    "optimization",
    "monitoring",
}
_COMMUNICATION_TERMS = {
    "collaborated",
    "stakeholders",
    "presented",
    "mentored",
    "led",
    "communicated",
    "cross-functional",
}
_FEATURE_NAMES = (
    "ats_score",
    "keyword_density",
    "quantified_achievements",
    "project_complexity_score",
    "skill_diversity",
    "education_strength",
    "experience_depth",
    "readability_score",
    "formatting_consistency",
    "action_verb_usage",
)


@dataclass(slots=True)
class ResumeCorrelationService:
    """Learns associations between resume patterns and downstream outcomes."""

    repository: HuntRepository

    def fingerprint_application_batch(
        self,
        *,
        user_id: str,
        applications: list[Application],
    ) -> dict[str, ResumeFingerprint]:
        return {
            application.application_id: self.build_fingerprint(
                user_id=user_id,
                resume_id=f"{application.resume_version}:{application.application_id}",
                resume_version=application.resume_version,
                content=application.resume.full_text
                or "\n".join(
                    [
                        application.resume.summary,
                        application.resume.skills_section,
                        application.resume.experience_section,
                    ]
                ),
            )
            for application in applications
        }

    async def analyze_resume(
        self,
        *,
        user_id: str,
        resume_id: str,
        resume_version: str | None,
        content: str,
    ) -> ResumeFingerprint:
        fingerprint = self.build_fingerprint(
            user_id=user_id,
            resume_id=resume_id,
            resume_version=resume_version or resume_id,
            content=content,
        )
        await self.repository.upsert_resume_fingerprint(fingerprint)
        await self.refresh_profile(user_id)
        return fingerprint

    async def analyze_resume_report(
        self,
        *,
        user_id: str,
        resume_id: str,
        resume_version: str | None,
        content: str,
        target_role: str | None = None,
    ) -> ResumeIntelligenceReport:
        """Persist a resume version and return a full deterministic intelligence report."""

        fingerprint = self.build_fingerprint(
            user_id=user_id,
            resume_id=resume_id,
            resume_version=resume_version or resume_id,
            content=content,
        )
        await self.repository.upsert_resume_fingerprint(fingerprint)
        profile = await self.refresh_profile(user_id)
        return self.build_report(
            fingerprint=fingerprint,
            content=content,
            target_role=target_role,
            profile=profile,
        )

    def build_report(
        self,
        *,
        fingerprint: ResumeFingerprint,
        content: str,
        target_role: str | None,
        profile: ResumeCorrelationProfile,
    ) -> ResumeIntelligenceReport:
        semantic_profile = self.extract_semantics(content, fingerprint.features)
        ats = self.score_ats(
            content=content,
            features=fingerprint.features,
            semantic_profile=semantic_profile,
            target_role=target_role,
        )
        weaknesses = self.detect_weaknesses(
            content=content,
            features=fingerprint.features,
            semantic_profile=semantic_profile,
            ats=ats,
            target_role=target_role,
        )
        prediction = self.predict_optimization(
            fingerprint=fingerprint,
            ats=ats,
            profile=profile,
        )
        return ResumeIntelligenceReport(
            fingerprint=fingerprint,
            semantic_profile=semantic_profile,
            ats=ats,
            weaknesses=weaknesses,
            optimization_prediction=prediction,
            generated_at=utc_now(),
        )

    def build_fingerprint(
        self,
        *,
        user_id: str,
        resume_id: str,
        resume_version: str,
        content: str,
    ) -> ResumeFingerprint:
        normalized = self._normalize(content)
        content_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        fingerprint_id = hashlib.sha256(f"{user_id}:{content_hash}".encode("utf-8")).hexdigest()
        now = utc_now()
        return ResumeFingerprint(
            fingerprint_id=fingerprint_id,
            user_id=user_id,
            resume_id=resume_id,
            resume_version=resume_version,
            content_hash=content_hash,
            features=self.extract_features(content),
            created_at=now,
            updated_at=now,
        )

    def extract_features(self, content: str) -> ResumeFeatures:
        normalized = self._normalize(content)
        words = re.findall(r"[a-z0-9]+", normalized)
        word_count = max(len(words), 1)
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        bullet_lines = [line for line in lines if line.startswith(("-", "*", "•"))]
        sentence_lengths = [
            len(re.findall(r"[a-z0-9]+", sentence.lower()))
            for sentence in re.split(r"[.!?]+", content)
            if sentence.strip()
        ]

        technical_hits = self._phrase_hits(normalized, _TECHNICAL_KEYWORDS)
        keyword_density = min(1.0, (technical_hits / word_count) * 18)
        quantified_achievements = len(re.findall(r"\b\d+(?:\.\d+)?%?\b", content))
        project_complexity_score = min(
            1.0,
            self._phrase_hits(normalized, _PROJECT_COMPLEXITY_TERMS) / 5,
        )
        skill_clusters = sum(
            bool(self._phrase_hits(normalized, terms))
            for terms in (_BACKEND_KEYWORDS, _FRONTEND_KEYWORDS, _DATA_KEYWORDS)
        )
        skill_diversity = round(skill_clusters / 3, 4)
        education_strength = self._education_strength(normalized)
        experience_depth = min(
            1.0,
            (
                self._phrase_hits(normalized, _PROJECT_COMPLEXITY_TERMS)
                + len(re.findall(r"\b\d+\+?\s+years?\b", normalized))
                + self._phrase_hits(normalized, _ACTION_VERBS)
            )
            / 10,
        )
        readability_score = self._readability(sentence_lengths)
        formatting_consistency = self._formatting_consistency(lines, bullet_lines)
        action_verb_usage = min(1.0, self._phrase_hits(normalized, _ACTION_VERBS) / max(len(lines), 1))
        backend_keywords = self._phrase_hits(normalized, _BACKEND_KEYWORDS)
        frontend_keywords = self._phrase_hits(normalized, _FRONTEND_KEYWORDS)
        data_keywords = self._phrase_hits(normalized, _DATA_KEYWORDS)
        technical_depth = min(
            1.0,
            (backend_keywords + frontend_keywords + data_keywords + technical_hits) / 16,
        )
        communication_indicators = min(
            1.0,
            self._phrase_hits(normalized, _COMMUNICATION_TERMS) / 5,
        )
        ats_score = round(
            (
                keyword_density * 0.25
                + min(1.0, quantified_achievements / 6) * 0.15
                + readability_score * 0.15
                + formatting_consistency * 0.15
                + action_verb_usage * 0.15
                + technical_depth * 0.15
            )
            * 100,
            2,
        )
        return ResumeFeatures(
            ats_score=ats_score,
            keyword_density=round(keyword_density, 4),
            quantified_achievements=quantified_achievements,
            project_complexity_score=round(project_complexity_score, 4),
            skill_diversity=skill_diversity,
            education_strength=round(education_strength, 4),
            experience_depth=round(experience_depth, 4),
            readability_score=round(readability_score, 4),
            formatting_consistency=round(formatting_consistency, 4),
            action_verb_usage=round(action_verb_usage, 4),
            backend_keywords=backend_keywords,
            frontend_keywords=frontend_keywords,
            data_keywords=data_keywords,
            technical_depth=round(technical_depth, 4),
            communication_indicators=round(communication_indicators, 4),
        )

    def extract_semantics(
        self,
        content: str,
        features: ResumeFeatures,
    ) -> ResumeSemanticProfile:
        normalized = self._normalize(content)
        skills = sorted(
            {
                keyword.title() if len(keyword) > 3 else keyword.upper()
                for keyword in _TECHNICAL_KEYWORDS
                if keyword in normalized
            }
        )
        technologies = sorted(
            {
                keyword
                for keyword in (
                    _BACKEND_KEYWORDS
                    | _FRONTEND_KEYWORDS
                    | _DATA_KEYWORDS
                    | {"docker", "kubernetes", "redis", "postgres", "aws", "terraform"}
                )
                if keyword in normalized
            }
        )
        leadership = sorted(
            {
                term
                for term in _COMMUNICATION_TERMS | {"owned", "coached", "managed", "architected"}
                if term in normalized
            }
        )
        domain_scores = {
            "backend": min(1.0, features.backend_keywords / 8),
            "frontend": min(1.0, features.frontend_keywords / 8),
            "data": min(1.0, features.data_keywords / 8),
            "platform": min(1.0, self._phrase_hits(normalized, {"docker", "kubernetes", "terraform", "redis"}) / 6),
        }
        bullet_count = max(
            1,
            len([line for line in content.splitlines() if line.strip().startswith(("-", "*", "•"))]),
        )
        return ResumeSemanticProfile(
            skills=skills,
            technologies=technologies,
            quantified_impact=features.quantified_achievements,
            project_complexity=features.project_complexity_score,
            leadership_signals=leadership,
            domain_specialization={key: round(value, 4) for key, value in domain_scores.items()},
            achievement_density=round(min(1.0, features.quantified_achievements / bullet_count), 4),
        )

    def score_ats(
        self,
        *,
        content: str,
        features: ResumeFeatures,
        semantic_profile: ResumeSemanticProfile,
        target_role: str | None,
    ) -> ATSBreakdown:
        normalized = self._normalize(content)
        sections = {"skills", "experience", "projects", "education"}
        section_hits = sum(1 for section in sections if section in normalized)
        structure_quality = min(1.0, section_hits / len(sections) + 0.10)
        keyword_relevance = min(1.0, features.keyword_density * 1.25)
        quantified_metrics = min(1.0, features.quantified_achievements / 6)
        role_alignment = self._role_alignment(normalized, target_role)
        strongest_domain = max(semantic_profile.domain_specialization.values() or [0.0])
        semantic_similarity = round(role_alignment * 0.55 + strongest_domain * 0.45, 4)
        final_score = round(
            (
                keyword_relevance * 0.22
                + features.formatting_consistency * 0.14
                + structure_quality * 0.16
                + features.readability_score * 0.14
                + quantified_metrics * 0.14
                + role_alignment * 0.12
                + semantic_similarity * 0.08
            )
            * 100,
            2,
        )
        return ATSBreakdown(
            keyword_relevance=round(keyword_relevance, 4),
            formatting_quality=features.formatting_consistency,
            structure_quality=round(structure_quality, 4),
            readability=features.readability_score,
            quantified_metrics=round(quantified_metrics, 4),
            role_alignment=round(role_alignment, 4),
            semantic_similarity=semantic_similarity,
            final_score=final_score,
        )

    def detect_weaknesses(
        self,
        *,
        content: str,
        features: ResumeFeatures,
        semantic_profile: ResumeSemanticProfile,
        ats: ATSBreakdown,
        target_role: str | None,
    ) -> list[ResumeWeakness]:
        weaknesses: list[ResumeWeakness] = []

        def add(category: str, severity: str, explanation: str, suggestion: str, impact: float) -> None:
            weaknesses.append(
                ResumeWeakness(
                    weakness_id=hashlib.sha256(f"{category}:{explanation}".encode("utf-8")).hexdigest()[:12],
                    category=category,
                    severity=severity,
                    explanation=explanation,
                    optimization_suggestion=suggestion,
                    expected_ats_impact=round(impact, 2),
                )
            )

        vague_bullets = [
            line.strip()
            for line in content.splitlines()
            if re.search(r"\b(responsible for|worked on|helped|handled|various)\b", line.lower())
        ]
        if vague_bullets:
            add(
                "low_impact_language",
                "high" if len(vague_bullets) >= 3 else "medium",
                "Some bullets describe activity instead of measurable ownership or outcome.",
                "Rewrite vague bullets with action verb, scope, metric, and business/technical result.",
                6.0 + min(8.0, len(vague_bullets) * 2.0),
            )
        if features.quantified_achievements < 2:
            add(
                "lack_of_metrics",
                "high",
                "The resume has too few quantified achievements for strong ATS and recruiter signal.",
                "Add numbers for latency, cost, scale, users, revenue, automation time saved, or accuracy gains.",
                12.0,
            )
        if features.keyword_density < 0.28:
            add(
                "poor_role_targeting",
                "medium",
                "Technical keyword density is low for targeted job matching.",
                "Mirror important role-specific terms from target job descriptions without keyword stuffing.",
                7.5,
            )
        if features.project_complexity_score < 0.35:
            add(
                "weak_projects",
                "medium",
                "Projects do not yet show enough system complexity or engineering depth.",
                "Mention architecture, scale, reliability, data flow, integrations, or performance constraints.",
                6.5,
            )
        if features.formatting_consistency < 0.70 or ats.structure_quality < 0.65:
            add(
                "ats_incompatibility",
                "medium",
                "Structure or formatting may make parsing less reliable.",
                "Use clear section headings, consistent bullets, simple formatting, and avoid dense paragraphs.",
                8.0,
            )
        if semantic_profile.achievement_density < 0.35:
            add(
                "achievement_density",
                "medium",
                "A low share of bullets contain concrete achievements.",
                "Turn responsibilities into outcome bullets and quantify at least every second bullet.",
                5.5,
            )
        if target_role and ats.role_alignment < 0.45:
            add(
                "role_alignment",
                "high",
                f"The resume is not strongly aligned to the target role '{target_role}'.",
                "Add a tailored summary, project ordering, and skills section for this role family.",
                10.0,
            )
        return weaknesses

    def predict_optimization(
        self,
        *,
        fingerprint: ResumeFingerprint,
        ats: ATSBreakdown,
        profile: ResumeCorrelationProfile,
    ) -> ResumeOptimizationPrediction:
        estimate = profile.resume_effectiveness.get(fingerprint.fingerprint_id)
        ats_probability = round(ats.final_score / 100, 4)
        if estimate is None:
            interview_probability = round(0.25 * 0.55 + ats_probability * 0.45, 4)
            confidence = round(min(0.35, profile.total_linked_outcomes / 30), 4)
            evidence = ["No outcome history for this exact resume; structural ATS signals dominate."]
        else:
            interview_probability = round(
                estimate.interview_rate * 0.50
                + estimate.response_speed_score * 0.15
                + ats_probability * 0.25
                + estimate.consistency_score * 0.10,
                4,
            )
            confidence = estimate.confidence
            evidence = [
                f"{estimate.data_volume} linked outcomes for this resume pattern.",
                estimate.reason,
            ]
        rejection_likelihood = round(max(0.0, min(1.0, 1 - interview_probability * 0.85 - ats_probability * 0.15)), 4)
        return ResumeOptimizationPrediction(
            interview_probability=interview_probability,
            ats_probability=ats_probability,
            rejection_likelihood=rejection_likelihood,
            confidence=confidence,
            uncertainty=round(1 - confidence, 4),
            evidence=evidence,
        )

    async def compare_resume_versions(
        self,
        *,
        user_id: str,
        left_resume_id: str,
        right_resume_id: str,
    ) -> ResumeVersionComparison | None:
        left = await self.repository.get_resume_fingerprint(user_id, left_resume_id)
        right = await self.repository.get_resume_fingerprint(user_id, right_resume_id)
        if left is None or right is None:
            return None
        left_features = left.features
        right_features = right.features
        deltas = {
            name: round(
                self._normalised_feature_value(right_features, name)
                - self._normalised_feature_value(left_features, name),
                4,
            )
            for name in _FEATURE_NAMES
        }
        ats_delta = round(right_features.ats_score - left_features.ats_score, 2)
        stronger = (
            right.resume_id
            if ats_delta > 0
            else left.resume_id
            if ats_delta < 0
            else None
        )
        return ResumeVersionComparison(
            left_resume_id=left_resume_id,
            right_resume_id=right_resume_id,
            ats_delta=ats_delta,
            feature_deltas=deltas,
            stronger_version=stronger,
            explanation=(
                "Right version has stronger deterministic ATS indicators."
                if ats_delta > 0
                else "Left version has stronger deterministic ATS indicators."
                if ats_delta < 0
                else "Both versions are currently tied on deterministic ATS score."
            ),
        )

    async def get_profile(self, user_id: str) -> ResumeCorrelationProfile:
        profile = await self.repository.get_resume_correlation_profile(user_id)
        if profile is not None:
            return profile
        return await self.refresh_profile(user_id)

    async def get_resume_effectiveness(
        self,
        *,
        user_id: str,
        resume_id: str,
    ) -> ResumeEffectivenessEstimate | None:
        profile = await self.get_profile(user_id)
        for estimate in profile.resume_effectiveness.values():
            if estimate.resume_id == resume_id:
                return estimate
        return None

    async def refresh_profile(self, user_id: str) -> ResumeCorrelationProfile:
        applications = await self.repository.list_all_application_records(user_id)
        recommendations, behaviors, outcomes = await self.repository.list_abc_records(user_id)
        del recommendations  # The resume engine needs linked actions/outcomes, not shown-job history.
        fingerprint_ids = [
            application.resume_fingerprint_id
            for application in applications
            if application.resume_fingerprint_id
        ]
        linked_fingerprints = await self.repository.get_resume_fingerprint_records_by_ids(
            fingerprint_ids
        )
        all_fingerprints = {
            fingerprint.fingerprint_id: fingerprint
            for fingerprint in await self.repository.list_resume_fingerprints(user_id)
        }
        fingerprints = {**all_fingerprints, **linked_fingerprints}
        linked_rows = self._linked_rows(applications, behaviors, outcomes, fingerprints)
        correlations = self._feature_correlations(linked_rows)
        effectiveness = self._resume_effectiveness(linked_rows, fingerprints)
        profile = ResumeCorrelationProfile(
            user_id=user_id,
            feature_correlations=correlations,
            resume_effectiveness=effectiveness,
            total_linked_outcomes=len(linked_rows),
            updated_at=utc_now(),
        )
        await self.repository.upsert_resume_correlation_profile(profile)
        return profile

    @staticmethod
    def _linked_rows(
        applications: list[ApplicationRecord],
        behaviors: list[BehaviorEventRecord],
        outcomes: list[OutcomeRecord],
        fingerprints: dict[str, ResumeFingerprint],
    ) -> list[tuple[ApplicationRecord, ResumeFingerprint, OutcomeRecord]]:
        application_by_context = {
            (application.hunt_id, application.job_id): application
            for application in applications
        }
        behavior_by_id = {behavior.id: behavior for behavior in behaviors}
        rows: list[tuple[ApplicationRecord, ResumeFingerprint, OutcomeRecord]] = []
        for outcome in outcomes:
            behavior = behavior_by_id.get(outcome.behavior_event_id)
            if behavior is None:
                continue
            application = application_by_context.get((behavior.hunt_id, behavior.job_id))
            if application is None or application.resume_fingerprint_id is None:
                continue
            fingerprint = fingerprints.get(application.resume_fingerprint_id)
            if fingerprint is None:
                continue
            rows.append((application, fingerprint, outcome))
        return rows

    def _feature_correlations(
        self,
        rows: list[tuple[ApplicationRecord, ResumeFingerprint, OutcomeRecord]],
    ) -> dict[str, FeatureCorrelation]:
        if not rows:
            return {
                name: FeatureCorrelation(
                    interview_correlation=0.0,
                    rejection_correlation=0.0,
                    response_speed_correlation=0.0,
                    offer_correlation=0.0,
                    confidence=0.0,
                    data_volume=0,
                    uncertainty=1.0,
                )
                for name in _FEATURE_NAMES
            }

        outcomes = {
            "interview": [
                1.0
                if outcome.outcome_type in {
                    OutcomeType.INTERVIEW.value,
                    OutcomeType.OFFER.value,
                    OutcomeType.FOLLOW_UP_REQUESTED.value,
                }
                else 0.0
                for _, _, outcome in rows
            ],
            "rejection": [
                1.0
                if outcome.outcome_type in {
                    OutcomeType.REJECTION.value,
                    OutcomeType.NO_RESPONSE.value,
                }
                else 0.0
                for _, _, outcome in rows
            ],
            "response_speed": [
                min(1.0, 1 / max(outcome.response_time_days, 1.0))
                for _, _, outcome in rows
            ],
            "offer": [
                1.0 if outcome.outcome_type == OutcomeType.OFFER.value else 0.0
                for _, _, outcome in rows
            ],
        }
        correlations: dict[str, FeatureCorrelation] = {}
        n = len(rows)
        sample_confidence = min(1.0, n / 20)
        for name in _FEATURE_NAMES:
            values = [self._normalised_feature_value(row[1].features, name) for row in rows]
            raw = {
                key: self._pearson(values, targets)
                for key, targets in outcomes.items()
            }
            shrinkage = n / (n + 8)
            signal_strength = max(abs(value) for value in raw.values())
            confidence = round(sample_confidence * min(1.0, 0.35 + signal_strength), 4)
            correlations[name] = FeatureCorrelation(
                interview_correlation=round(raw["interview"] * shrinkage, 4),
                rejection_correlation=round(raw["rejection"] * shrinkage, 4),
                response_speed_correlation=round(raw["response_speed"] * shrinkage, 4),
                offer_correlation=round(raw["offer"] * shrinkage, 4),
                confidence=confidence,
                data_volume=n,
                uncertainty=round(1 - confidence, 4),
            )
        return correlations

    def _resume_effectiveness(
        self,
        rows: list[tuple[ApplicationRecord, ResumeFingerprint, OutcomeRecord]],
        fingerprints: dict[str, ResumeFingerprint],
    ) -> dict[str, ResumeEffectivenessEstimate]:
        outcomes_by_fingerprint: dict[str, list[OutcomeRecord]] = defaultdict(list)
        for _, fingerprint, outcome in rows:
            outcomes_by_fingerprint[fingerprint.fingerprint_id].append(outcome)

        estimates: dict[str, ResumeEffectivenessEstimate] = {}
        for fingerprint in fingerprints.values():
            resume_outcomes = outcomes_by_fingerprint.get(fingerprint.fingerprint_id, [])
            data_volume = len(resume_outcomes)
            interview_hits = sum(
                1
                for outcome in resume_outcomes
                if outcome.outcome_type
                in {
                    OutcomeType.INTERVIEW.value,
                    OutcomeType.OFFER.value,
                    OutcomeType.FOLLOW_UP_REQUESTED.value,
                }
            )
            interview_rate = self._smoothed_rate(interview_hits, data_volume, prior=0.25)
            response_speed_score = self._smoothed_response_speed(resume_outcomes)
            ats_score_component = round(fingerprint.features.ats_score / 100, 4)
            consistency_score = round(
                (
                    fingerprint.features.readability_score
                    + fingerprint.features.formatting_consistency
                    + fingerprint.features.action_verb_usage
                )
                / 3,
                4,
            )
            score = round(
                interview_rate * 0.40
                + response_speed_score * 0.20
                + ats_score_component * 0.20
                + consistency_score * 0.20,
                4,
            )
            confidence = round(min(1.0, data_volume / 10), 4)
            estimates[fingerprint.fingerprint_id] = ResumeEffectivenessEstimate(
                resume_id=fingerprint.resume_id,
                fingerprint_id=fingerprint.fingerprint_id,
                resume_version=fingerprint.resume_version,
                effectiveness_score=score,
                interview_rate=interview_rate,
                response_speed_score=response_speed_score,
                ats_score_component=ats_score_component,
                consistency_score=consistency_score,
                confidence=confidence,
                data_volume=data_volume,
                uncertainty=round(1 - confidence, 4),
                reason=(
                    "Outcome-linked estimate with meaningful evidence"
                    if confidence >= 0.5
                    else "Sparse outcome data; structural quality carries more weight than observed results"
                ),
            )
        return estimates

    @staticmethod
    def _normalised_feature_value(features: ResumeFeatures, name: str) -> float:
        value = getattr(features, name)
        if name == "ats_score":
            return value / 100
        if name == "quantified_achievements":
            return min(1.0, value / 10)
        return float(value)

    @staticmethod
    def _role_alignment(text: str, target_role: str | None) -> float:
        if not target_role:
            return 0.55
        role_terms = {
            token
            for token in re.findall(r"[a-z0-9]+", target_role.lower())
            if len(token) > 2 and token not in {"and", "the", "job", "role"}
        }
        if not role_terms:
            return 0.55
        matched = sum(1 for term in role_terms if term in text)
        related_bonus = 0.0
        if "backend" in role_terms and _BACKEND_KEYWORDS & set(re.findall(r"[a-z0-9]+", text)):
            related_bonus += 0.20
        if "frontend" in role_terms and _FRONTEND_KEYWORDS & set(re.findall(r"[a-z0-9]+", text)):
            related_bonus += 0.20
        if "data" in role_terms and _DATA_KEYWORDS & set(re.findall(r"[a-z0-9]+", text)):
            related_bonus += 0.20
        return round(min(1.0, matched / len(role_terms) + related_bonus), 4)

    @staticmethod
    def _pearson(xs: list[float], ys: list[float]) -> float:
        if len(xs) < 2 or len(xs) != len(ys):
            return 0.0
        x_mean = fmean(xs)
        y_mean = fmean(ys)
        x_std = pstdev(xs)
        y_std = pstdev(ys)
        if math.isclose(x_std, 0.0) or math.isclose(y_std, 0.0):
            return 0.0
        covariance = fmean((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys, strict=False))
        return max(-1.0, min(1.0, covariance / (x_std * y_std)))

    @staticmethod
    def _smoothed_rate(numerator: int, denominator: int, *, prior: float) -> float:
        return round((numerator + prior * 4) / (denominator + 4), 4)

    @staticmethod
    def _smoothed_response_speed(outcomes: list[OutcomeRecord]) -> float:
        if not outcomes:
            return 0.35
        observed = [min(1.0, 1 / max(outcome.response_time_days, 1.0)) for outcome in outcomes]
        return round((sum(observed) + 0.35 * 4) / (len(observed) + 4), 4)

    @staticmethod
    def _normalize(content: str) -> str:
        return " ".join(content.lower().split())

    @staticmethod
    def _phrase_hits(text: str, phrases: set[str]) -> int:
        return sum(text.count(phrase) for phrase in phrases)

    @staticmethod
    def _education_strength(text: str) -> float:
        score = 0.0
        if any(term in text for term in {"bachelor", "b.sc", "btech", "degree"}):
            score += 0.35
        if any(term in text for term in {"master", "m.sc", "mba"}):
            score += 0.25
        if any(term in text for term in {"phd", "doctorate"}):
            score += 0.25
        if any(term in text for term in {"computer science", "engineering"}):
            score += 0.15
        return min(1.0, score)

    @staticmethod
    def _readability(sentence_lengths: list[int]) -> float:
        if not sentence_lengths:
            return 0.4
        average = fmean(sentence_lengths)
        ideal_distance = abs(average - 18) / 18
        return max(0.0, min(1.0, 1 - ideal_distance))

    @staticmethod
    def _formatting_consistency(lines: list[str], bullet_lines: list[str]) -> float:
        if not lines:
            return 0.0
        if not bullet_lines:
            return 0.6
        bullet_ratio = len(bullet_lines) / len(lines)
        consistent_prefixes = len({line[0] for line in bullet_lines}) == 1
        prefix_bonus = 0.2 if consistent_prefixes else 0.0
        return min(1.0, bullet_ratio + prefix_bonus)
