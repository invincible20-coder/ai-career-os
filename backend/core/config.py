"""
Application configuration for the production backend.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _split_csv_env(name: str, default: str) -> tuple[str, ...]:
    raw_value = os.getenv(name, default)
    return tuple(item.strip() for item in raw_value.split(",") if item.strip())


@dataclass(frozen=True, slots=True)
class Settings:
    """Immutable settings shared across the application."""

    app_name: str = "Autonomous Job Hunt AI Agent"
    app_version: str = "2.0.0"
    debug: bool = False
    log_level: str = "INFO"

    api_prefix: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = 8000

    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/job_hunt_agent"
    )

    cors_allowed_origins: tuple[str, ...] = ("http://localhost:3000",)
    cors_allow_credentials: bool = True

    llm_provider: str = "mock"
    use_mock_llm: bool = True
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.4
    openai_max_tokens: int = 2048
    llm_timeout_seconds: float = 20.0

    max_jobs_per_search: int = 10
    default_country: str = "India"
    request_timeout_seconds: float = 15.0
    step_retry_attempts: int = 3
    step_retry_base_delay_seconds: float = 0.5
    step_retry_max_delay_seconds: float = 4.0
    max_parallel_job_tasks: int = 4
    hunt_rate_limit_requests: int = 10
    hunt_rate_limit_window_seconds: int = 60
    behavior_min_applications: int = 5
    behavior_analysis_window_days: int = 30

    def validate(self) -> None:
        if self.cors_allow_credentials and "*" in self.cors_allowed_origins:
            raise ValueError(
                "CORS_ALLOW_CREDENTIALS=true cannot be combined with CORS_ALLOWED_ORIGINS=*"
            )
        if self.step_retry_attempts < 1:
            raise ValueError("STEP_RETRY_ATTEMPTS must be at least 1")
        if self.hunt_rate_limit_requests < 1:
            raise ValueError("HUNT_RATE_LIMIT_REQUESTS must be at least 1")
        if self.hunt_rate_limit_window_seconds < 1:
            raise ValueError("HUNT_RATE_LIMIT_WINDOW_SECONDS must be at least 1")
        if self.behavior_min_applications < 1:
            raise ValueError("BEHAVIOR_MIN_APPLICATIONS must be at least 1")
        if self.behavior_analysis_window_days < 1:
            raise ValueError("BEHAVIOR_ANALYSIS_WINDOW_DAYS must be at least 1")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load settings once from environment variables."""

    settings = Settings(
        app_name=os.getenv("APP_NAME", "Autonomous Job Hunt AI Agent"),
        app_version=os.getenv("APP_VERSION", "2.0.0"),
        debug=os.getenv("DEBUG", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        api_prefix=os.getenv("API_PREFIX", "/api/v1"),
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:postgres@localhost:5432/job_hunt_agent",
        ),
        cors_allowed_origins=_split_csv_env(
            "CORS_ALLOWED_ORIGINS",
            "http://localhost:3000",
        ),
        cors_allow_credentials=os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower()
        == "true",
        llm_provider=os.getenv("LLM_PROVIDER", "mock"),
        use_mock_llm=os.getenv("USE_MOCK_LLM", "true").lower() == "true",
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        openai_temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.4")),
        openai_max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "2048")),
        llm_timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "20.0")),
        max_jobs_per_search=int(os.getenv("MAX_JOBS_PER_SEARCH", "10")),
        default_country=os.getenv("DEFAULT_COUNTRY", "India"),
        request_timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "15.0")),
        step_retry_attempts=int(os.getenv("STEP_RETRY_ATTEMPTS", "3")),
        step_retry_base_delay_seconds=float(
            os.getenv("STEP_RETRY_BASE_DELAY_SECONDS", "0.5")
        ),
        step_retry_max_delay_seconds=float(
            os.getenv("STEP_RETRY_MAX_DELAY_SECONDS", "4.0")
        ),
        max_parallel_job_tasks=int(os.getenv("MAX_PARALLEL_JOB_TASKS", "4")),
        hunt_rate_limit_requests=int(os.getenv("HUNT_RATE_LIMIT_REQUESTS", "10")),
        hunt_rate_limit_window_seconds=int(
            os.getenv("HUNT_RATE_LIMIT_WINDOW_SECONDS", "60")
        ),
        behavior_min_applications=int(os.getenv("BEHAVIOR_MIN_APPLICATIONS", "5")),
        behavior_analysis_window_days=int(
            os.getenv("BEHAVIOR_ANALYSIS_WINDOW_DAYS", "30")
        ),
    )
    settings.validate()
    return settings
