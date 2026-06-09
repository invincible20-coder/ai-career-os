"""
Models for resume-outcome correlation and predictive career modeling.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ResumeAnalysisRequest(BaseModel):
    """Incoming resume payload for deterministic fingerprinting."""

    resume_id: str = Field(..., min_length=1, max_length=128)
    resume_version: str | None = Field(default=None, max_length=128)
    target_role: str | None = Field(default=None, max_length=255)
    content: str = Field(..., min_length=1, max_length=30000)


class ResumeFeatures(BaseModel):
    """Deterministic resume feature vector."""

    ats_score: float = Field(ge=0, le=100)
    keyword_density: float = Field(ge=0, le=1)
    quantified_achievements: int = Field(ge=0)
    project_complexity_score: float = Field(ge=0, le=1)
    skill_diversity: float = Field(ge=0, le=1)
    education_strength: float = Field(ge=0, le=1)
    experience_depth: float = Field(ge=0, le=1)
    readability_score: float = Field(ge=0, le=1)
    formatting_consistency: float = Field(ge=0, le=1)
    action_verb_usage: float = Field(ge=0, le=1)
    backend_keywords: int = Field(ge=0)
    frontend_keywords: int = Field(ge=0)
    data_keywords: int = Field(ge=0)
    technical_depth: float = Field(ge=0, le=1)
    communication_indicators: float = Field(ge=0, le=1)


class ResumeFingerprint(BaseModel):
    """Stored resume fingerprint tied to a concrete resume body."""

    fingerprint_id: str
    user_id: str
    resume_id: str
    resume_version: str
    content_hash: str
    features: ResumeFeatures
    created_at: datetime
    updated_at: datetime


class ResumeSemanticProfile(BaseModel):
    """Human-readable semantic extraction from one resume body."""

    skills: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    quantified_impact: int = Field(ge=0)
    project_complexity: float = Field(ge=0, le=1)
    leadership_signals: list[str] = Field(default_factory=list)
    domain_specialization: dict[str, float] = Field(default_factory=dict)
    achievement_density: float = Field(ge=0, le=1)


class ATSBreakdown(BaseModel):
    """Explainable ATS scoring components."""

    keyword_relevance: float = Field(ge=0, le=1)
    formatting_quality: float = Field(ge=0, le=1)
    structure_quality: float = Field(ge=0, le=1)
    readability: float = Field(ge=0, le=1)
    quantified_metrics: float = Field(ge=0, le=1)
    role_alignment: float = Field(ge=0, le=1)
    semantic_similarity: float = Field(ge=0, le=1)
    final_score: float = Field(ge=0, le=100)


class ResumeWeakness(BaseModel):
    """Actionable resume weakness with expected ATS impact."""

    weakness_id: str
    category: str
    severity: str
    explanation: str
    optimization_suggestion: str
    expected_ats_impact: float


class ResumeOptimizationPrediction(BaseModel):
    """Confidence-aware prediction for the current resume pattern."""

    interview_probability: float = Field(ge=0, le=1)
    ats_probability: float = Field(ge=0, le=1)
    rejection_likelihood: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    uncertainty: float = Field(ge=0, le=1)
    evidence: list[str] = Field(default_factory=list)


class ResumeIntelligenceReport(BaseModel):
    """Full deterministic resume intelligence output."""

    fingerprint: ResumeFingerprint
    semantic_profile: ResumeSemanticProfile
    ats: ATSBreakdown
    weaknesses: list[ResumeWeakness] = Field(default_factory=list)
    optimization_prediction: ResumeOptimizationPrediction
    generated_at: datetime


class ResumeVersionComparison(BaseModel):
    """Comparison between two stored resume versions."""

    left_resume_id: str
    right_resume_id: str
    ats_delta: float
    feature_deltas: dict[str, float] = Field(default_factory=dict)
    stronger_version: str | None = None
    explanation: str


class FeatureCorrelation(BaseModel):
    """Confidence-aware correlation estimate for one resume feature."""

    interview_correlation: float = Field(ge=-1, le=1)
    rejection_correlation: float = Field(ge=-1, le=1)
    response_speed_correlation: float = Field(ge=-1, le=1)
    offer_correlation: float = Field(ge=-1, le=1)
    confidence: float = Field(ge=0, le=1)
    data_volume: int = Field(ge=0)
    uncertainty: float = Field(ge=0, le=1)


class ResumeEffectivenessEstimate(BaseModel):
    """Probabilistic estimate of how well one resume pattern is performing."""

    resume_id: str
    fingerprint_id: str
    resume_version: str
    effectiveness_score: float = Field(ge=0, le=1)
    interview_rate: float = Field(ge=0, le=1)
    response_speed_score: float = Field(ge=0, le=1)
    ats_score_component: float = Field(ge=0, le=1)
    consistency_score: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    data_volume: int = Field(ge=0)
    uncertainty: float = Field(ge=0, le=1)
    reason: str


class ResumeCorrelationProfile(BaseModel):
    """Latest resume-learning state for one user."""

    user_id: str
    feature_correlations: dict[str, FeatureCorrelation] = Field(default_factory=dict)
    resume_effectiveness: dict[str, ResumeEffectivenessEstimate] = Field(default_factory=dict)
    total_linked_outcomes: int = 0
    updated_at: datetime


class CareerVector(BaseModel):
    """Weighted representation of one career archetype."""

    technical_depth: float = Field(ge=0, le=1)
    system_design: float = Field(ge=0, le=1)
    analytical_reasoning: float = Field(ge=0, le=1)
    communication: float = Field(ge=0, le=1)
    creativity: float = Field(ge=0, le=1)
    leadership: float = Field(ge=0, le=1)
    exploration_tendency: float = Field(ge=0, le=1)


class UserCareerVector(CareerVector):
    """Current evolving user vector."""


class CareerPrediction(BaseModel):
    """Probabilistic trajectory estimate for one career direction."""

    role: str
    category: str
    compatibility: float = Field(ge=0, le=1)
    growth_potential: float = Field(ge=0, le=1)
    trajectory_stability: float = Field(ge=0, le=1)
    persistence_probability: float = Field(ge=0, le=1)
    adaptability: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    uncertainty: float = Field(ge=0, le=1)
    reason: str


class PredictiveCareerProfile(BaseModel):
    """Latest long-term career modeling state for one user."""

    user_id: str
    user_vector: UserCareerVector
    predictions: list[CareerPrediction] = Field(default_factory=list)
    updated_at: datetime
