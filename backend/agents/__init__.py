"""
Agent bundle used by the orchestrator.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.agents.apply_agent import ApplicationAgent
from backend.agents.career_agent import CareerAgent
from backend.agents.cover_letter_agent import CoverLetterAgent
from backend.agents.job_finder import JobFinderAgent
from backend.agents.planner import PlannerAgent
from backend.agents.resume_agent import ResumeAgent
from backend.agents.tracker_agent import TrackingAgent


@dataclass(frozen=True, slots=True)
class AgentSuite:
    career_advisor: CareerAgent
    planner: PlannerAgent
    job_finder: JobFinderAgent
    resume_writer: ResumeAgent
    cover_letter_writer: CoverLetterAgent
    application_builder: ApplicationAgent
    tracker: TrackingAgent
