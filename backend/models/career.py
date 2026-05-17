"""
Career recommendation models.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    """Partial user profile used for career recommendations."""

    skills: list[str] = Field(default_factory=list)
    education: str | None = None
    interests: list[str] = Field(default_factory=list)
    experience: str | None = None
    preferred_locations: list[str] = Field(default_factory=list)
    github_topics: list[str] = Field(default_factory=list)
    learning_history: list[str] = Field(default_factory=list)

    def has_signal(self) -> bool:
        return bool(
            self.skills
            or self.interests
            or (self.education and self.education.strip())
            or (self.experience and self.experience.strip())
            or self.preferred_locations
            or self.github_topics
            or self.learning_history
        )

    def to_prompt_block(self) -> str:
        return (
            f"Skills: {', '.join(self.skills) or 'Not provided'}\n"
            f"Education: {self.education or 'Not provided'}\n"
            f"Interests: {', '.join(self.interests) or 'Not provided'}\n"
            f"Experience: {self.experience or 'Not provided'}\n"
            f"Preferred locations: {', '.join(self.preferred_locations) or 'Not provided'}\n"
            f"GitHub topics: {', '.join(self.github_topics) or 'Not provided'}\n"
            f"Learning history: {', '.join(self.learning_history) or 'Not provided'}"
        )


class RoleSuggestion(BaseModel):
    """One recommended role for the user."""

    role: str = Field(..., min_length=2, max_length=120)
    reason: str = Field(..., min_length=5, max_length=500)
    required_skills: list[str] = Field(default_factory=list)


class CareerRecommendation(BaseModel):
    """Structured output returned by the career agent."""

    recommended_roles: list[RoleSuggestion] = Field(default_factory=list)
