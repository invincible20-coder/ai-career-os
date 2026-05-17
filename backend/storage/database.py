"""
Async database wiring.
"""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from backend.storage.records import Base
from backend.storage.auth_records import UserRecord, LinkedAccountRecord, SessionRecord


class Database:
    """Owns the async engine and session factory."""

    def __init__(self, database_url: str) -> None:
        self.engine: AsyncEngine = create_async_engine(
            database_url,
            pool_pre_ping=True,
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )

    async def create_schema(self) -> None:
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
            await connection.run_sync(self._ensure_hunt_columns)
            await connection.run_sync(self._ensure_job_columns)
            await connection.run_sync(self._ensure_application_columns)
            await connection.run_sync(self._ensure_recommendation_event_columns)

    async def dispose(self) -> None:
        await self.engine.dispose()

    @staticmethod
    def _ensure_hunt_columns(connection) -> None:
        inspector = inspect(connection)
        if "hunts" not in inspector.get_table_names():
            return

        existing_columns = {column["name"] for column in inspector.get_columns("hunts")}
        dialect_name = connection.dialect.name
        statements: list[str] = []

        if "original_goal" not in existing_columns:
            statements.append("ALTER TABLE hunts ADD COLUMN original_goal TEXT")

        if "user_key" not in existing_columns:
            statements.append(
                "ALTER TABLE hunts ADD COLUMN user_key VARCHAR(255) NOT NULL DEFAULT 'anonymous'"
            )

        if "goal_was_recommended" not in existing_columns:
            if dialect_name == "postgresql":
                statements.append(
                    "ALTER TABLE hunts ADD COLUMN goal_was_recommended BOOLEAN NOT NULL DEFAULT FALSE"
                )
            else:
                statements.append(
                    "ALTER TABLE hunts ADD COLUMN goal_was_recommended BOOLEAN NOT NULL DEFAULT 0"
                )

        if "career_recommendation_json" not in existing_columns:
            if dialect_name == "postgresql":
                statements.append("ALTER TABLE hunts ADD COLUMN career_recommendation_json JSON")
            else:
                statements.append("ALTER TABLE hunts ADD COLUMN career_recommendation_json JSON")

        for statement in statements:
            connection.execute(text(statement))

    @staticmethod
    def _ensure_application_columns(connection) -> None:
        inspector = inspect(connection)
        if "applications" not in inspector.get_table_names():
            return

        existing_columns = {
            column["name"] for column in inspector.get_columns("applications")
        }
        dialect_name = connection.dialect.name
        statements: list[str] = []

        if "user_key" not in existing_columns:
            statements.append(
                "ALTER TABLE applications ADD COLUMN user_key VARCHAR(255) NOT NULL DEFAULT 'anonymous'"
            )
        if "role" not in existing_columns:
            statements.append(
                "ALTER TABLE applications ADD COLUMN role VARCHAR(255) NOT NULL DEFAULT ''"
            )
        if "platform" not in existing_columns:
            statements.append(
                "ALTER TABLE applications ADD COLUMN platform VARCHAR(128) NOT NULL DEFAULT 'unknown'"
            )
        if "resume_version" not in existing_columns:
            statements.append(
                "ALTER TABLE applications ADD COLUMN resume_version VARCHAR(128) NOT NULL DEFAULT 'standard-v1'"
            )
        if "resume_fingerprint_id" not in existing_columns:
            statements.append(
                "ALTER TABLE applications ADD COLUMN resume_fingerprint_id VARCHAR(64)"
            )
        if "timestamp_applied" not in existing_columns:
            if dialect_name == "postgresql":
                column_type = "TIMESTAMP WITH TIME ZONE"
                default_value = "CURRENT_TIMESTAMP"
            else:
                column_type = "DATETIME"
                default_value = "'1970-01-01 00:00:00'"
            statements.append(
                f"ALTER TABLE applications ADD COLUMN timestamp_applied {column_type} NOT NULL DEFAULT {default_value}"
            )
        if "application_status" not in existing_columns:
            statements.append(
                "ALTER TABLE applications ADD COLUMN application_status VARCHAR(32) NOT NULL DEFAULT 'no_response'"
            )
        if "is_referral" not in existing_columns:
            default_value = "FALSE" if dialect_name == "postgresql" else "0"
            statements.append(
                f"ALTER TABLE applications ADD COLUMN is_referral BOOLEAN NOT NULL DEFAULT {default_value}"
            )

        for statement in statements:
            connection.execute(text(statement))

    @staticmethod
    def _ensure_job_columns(connection) -> None:
        inspector = inspect(connection)
        if "jobs" not in inspector.get_table_names():
            return

        existing_columns = {column["name"] for column in inspector.get_columns("jobs")}
        statements: list[str] = []

        if "rank_position" not in existing_columns:
            statements.append("ALTER TABLE jobs ADD COLUMN rank_position INTEGER")
        if "base_match_score" not in existing_columns:
            statements.append("ALTER TABLE jobs ADD COLUMN base_match_score FLOAT")
        if "final_score" not in existing_columns:
            statements.append("ALTER TABLE jobs ADD COLUMN final_score FLOAT")
        if "recommendation_reason" not in existing_columns:
            statements.append("ALTER TABLE jobs ADD COLUMN recommendation_reason TEXT")
        if "recommendation_event_id" not in existing_columns:
            statements.append("ALTER TABLE jobs ADD COLUMN recommendation_event_id VARCHAR(36)")
        if "category" not in existing_columns:
            statements.append("ALTER TABLE jobs ADD COLUMN category VARCHAR(64)")

        for statement in statements:
            connection.execute(text(statement))

    @staticmethod
    def _ensure_recommendation_event_columns(connection) -> None:
        inspector = inspect(connection)
        if "recommendation_events" not in inspector.get_table_names():
            return

        existing_columns = {
            column["name"] for column in inspector.get_columns("recommendation_events")
        }
        statements: list[str] = []

        if "event_type" not in existing_columns:
            statements.append(
                "ALTER TABLE recommendation_events ADD COLUMN event_type VARCHAR(64) NOT NULL DEFAULT 'job_shown'"
            )

        for statement in statements:
            connection.execute(text(statement))
