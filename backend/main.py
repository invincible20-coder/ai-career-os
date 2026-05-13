"""
Application factory and startup lifecycle.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.agents import AgentSuite
from backend.agents.apply_agent import ApplicationAgent
from backend.agents.career_agent import CareerAgent
from backend.agents.cover_letter_agent import CoverLetterAgent
from backend.agents.job_finder import JobFinderAgent
from backend.agents.planner import PlannerAgent
from backend.agents.resume_agent import ResumeAgent
from backend.agents.tracker_agent import TrackingAgent
from backend.api import router
from backend.api.errors import register_exception_handlers
from backend.core.config import Settings, get_settings
from backend.core.llm import OpenAIJSONClient
from backend.core.logger import configure_logging, get_logger
from backend.storage import Database


def _build_agent_suite(settings: Settings) -> AgentSuite:
    llm_client = OpenAIJSONClient(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        default_temperature=settings.openai_temperature,
        default_max_tokens=settings.openai_max_tokens,
        timeout_seconds=settings.llm_timeout_seconds,
    )
    return AgentSuite(
        career_advisor=CareerAgent(llm_client),
        planner=PlannerAgent(llm_client),
        job_finder=JobFinderAgent(
            default_country=settings.default_country,
            max_jobs_per_search=settings.max_jobs_per_search,
        ),
        resume_writer=ResumeAgent(llm_client),
        cover_letter_writer=CoverLetterAgent(llm_client),
        application_builder=ApplicationAgent(),
        tracker=TrackingAgent(),
    )


def create_app(
    *,
    settings: Settings | None = None,
    agents: AgentSuite | None = None,
    database: Database | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = settings or get_settings()
    configure_logging(settings.log_level)
    logger = get_logger(__name__)

    database = database or Database(settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = settings
        app.state.db = database
        app.state.agents = agents or _build_agent_suite(settings)
        await database.create_schema()
        logger.info(
            "app_startup",
            extra={
                "event": "app_startup",
                "api_prefix": settings.api_prefix,
                "allowed_origins": list(settings.cors_allowed_origins),
            },
        )
        yield
        await database.dispose()
        logger.info("app_shutdown", extra={"event": "app_shutdown"})

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allowed_origins),
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    register_exception_handlers(app)
    app.include_router(router, prefix=settings.api_prefix)
    return app


app = create_app()


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
