"""
Dual Memory Manager — Short-term and Long-term memory for behavioral intelligence.

Short-term memory decays quickly (7-day half-life) and tracks recent signals.
Long-term memory decays slowly (90-day half-life) and tracks stable preferences.
Both memories influence job ranking.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from math import pow

from backend.models.abc_intelligence import (
    DualMemoryState,
    LongTermMemory,
    MemoryEntry,
    ShortTermMemory,
)
from backend.storage.records import utc_now
from backend.storage.repository import HuntRepository

_SHORT_TERM_HALF_LIFE_DAYS = 7.0
_LONG_TERM_HALF_LIFE_DAYS = 90.0
_SHORT_TERM_MAX_ENTRIES = 50
_LONG_TERM_MAX_ENTRIES = 100
_PROMOTION_THRESHOLD = 3  # occurrences before promoting to long-term


@dataclass(slots=True)
class MemoryService:
    """Manages the dual memory system: short-term recency + long-term stability."""

    repository: HuntRepository

    async def get_memory_state(self, user_id: str) -> DualMemoryState:
        """Return the combined dual memory for ranking influence."""
        now = utc_now()
        short_term = await self._load_short_term(user_id, now)
        long_term = await self._load_long_term(user_id, now)
        return DualMemoryState(
            user_id=user_id,
            short_term=short_term,
            long_term=long_term,
            updated_at=now,
        )

    async def update_short_term(
        self,
        user_id: str,
        *,
        interest: str | None = None,
        search: str | None = None,
        application: str | None = None,
        goal: str | None = None,
        category: str = "general",
    ) -> ShortTermMemory:
        """Add a recent signal to short-term memory and apply fast decay."""
        now = utc_now()
        short_term = await self._load_short_term(user_id, now)

        if interest:
            short_term.recent_interests = self._upsert_entry(
                short_term.recent_interests, interest, category, now,
            )
        if search:
            short_term.recent_searches = self._upsert_entry(
                short_term.recent_searches, search, category, now,
            )
        if application:
            short_term.recent_applications = self._upsert_entry(
                short_term.recent_applications, application, category, now,
            )
        if goal:
            short_term.recent_goals = self._upsert_entry(
                short_term.recent_goals, goal, category, now,
            )

        short_term.updated_at = now

        # Promote frequently occurring items to long-term memory
        await self._promote_to_long_term(user_id, short_term, now)

        await self.repository.upsert_short_term_memory(
            user_id,
            recent_interests=[e.model_dump(mode="json") for e in short_term.recent_interests],
            recent_searches=[e.model_dump(mode="json") for e in short_term.recent_searches],
            recent_applications=[e.model_dump(mode="json") for e in short_term.recent_applications],
            recent_goals=[e.model_dump(mode="json") for e in short_term.recent_goals],
        )
        return short_term

    async def update_long_term(
        self,
        user_id: str,
        *,
        preference: str | None = None,
        successful_pattern: str | None = None,
        skill: str | None = None,
        category: str = "general",
    ) -> LongTermMemory:
        """Add a stable signal to long-term memory with slow decay."""
        now = utc_now()
        long_term = await self._load_long_term(user_id, now)

        if preference:
            long_term.stable_preferences = self._upsert_entry(
                long_term.stable_preferences, preference, category, now,
            )
        if successful_pattern:
            long_term.successful_patterns = self._upsert_entry(
                long_term.successful_patterns, successful_pattern, category, now,
            )
        if skill:
            long_term.persistent_skills = self._upsert_entry(
                long_term.persistent_skills, skill, category, now,
            )

        long_term.updated_at = now
        await self.repository.upsert_long_term_memory(
            user_id,
            stable_preferences=[e.model_dump(mode="json") for e in long_term.stable_preferences],
            successful_patterns=[e.model_dump(mode="json") for e in long_term.successful_patterns],
            persistent_skills=[e.model_dump(mode="json") for e in long_term.persistent_skills],
        )
        return long_term

    def memory_influenced_score(
        self,
        memory_state: DualMemoryState,
        job_category: str,
        job_keywords: set[str],
    ) -> float:
        """Blend short-term recency with long-term stability into a [0,1] score."""
        now = utc_now()
        short_term_score = self._category_signal(
            memory_state.short_term.recent_interests
            + memory_state.short_term.recent_applications
            + memory_state.short_term.recent_goals,
            job_category,
            job_keywords,
            now,
            _SHORT_TERM_HALF_LIFE_DAYS,
        )
        long_term_score = self._category_signal(
            memory_state.long_term.stable_preferences
            + memory_state.long_term.successful_patterns
            + memory_state.long_term.persistent_skills,
            job_category,
            job_keywords,
            now,
            _LONG_TERM_HALF_LIFE_DAYS,
        )
        # Short-term dominates for recency, long-term provides stability
        return round(min(1.0, short_term_score * 0.55 + long_term_score * 0.45), 4)

    async def _load_short_term(self, user_id: str, now: datetime) -> ShortTermMemory:
        record = await self.repository.get_short_term_memory(user_id)
        if record is None:
            return ShortTermMemory(user_id=user_id, updated_at=now)
        return ShortTermMemory(
            user_id=user_id,
            recent_interests=self._decay_entries(
                [MemoryEntry(**e) for e in record.recent_interests_json],
                now,
                _SHORT_TERM_HALF_LIFE_DAYS,
            ),
            recent_searches=self._decay_entries(
                [MemoryEntry(**e) for e in record.recent_searches_json],
                now,
                _SHORT_TERM_HALF_LIFE_DAYS,
            ),
            recent_applications=self._decay_entries(
                [MemoryEntry(**e) for e in record.recent_applications_json],
                now,
                _SHORT_TERM_HALF_LIFE_DAYS,
            ),
            recent_goals=self._decay_entries(
                [MemoryEntry(**e) for e in record.recent_goals_json],
                now,
                _SHORT_TERM_HALF_LIFE_DAYS,
            ),
            updated_at=record.updated_at,
        )

    async def _load_long_term(self, user_id: str, now: datetime) -> LongTermMemory:
        record = await self.repository.get_long_term_memory(user_id)
        if record is None:
            return LongTermMemory(user_id=user_id, updated_at=now)
        return LongTermMemory(
            user_id=user_id,
            stable_preferences=self._decay_entries(
                [MemoryEntry(**e) for e in record.stable_preferences_json],
                now,
                _LONG_TERM_HALF_LIFE_DAYS,
            ),
            successful_patterns=self._decay_entries(
                [MemoryEntry(**e) for e in record.successful_patterns_json],
                now,
                _LONG_TERM_HALF_LIFE_DAYS,
            ),
            persistent_skills=self._decay_entries(
                [MemoryEntry(**e) for e in record.persistent_skills_json],
                now,
                _LONG_TERM_HALF_LIFE_DAYS,
            ),
            updated_at=record.updated_at,
        )

    async def _promote_to_long_term(
        self,
        user_id: str,
        short_term: ShortTermMemory,
        now: datetime,
    ) -> None:
        """Promote frequently occurring short-term items to long-term memory."""
        all_entries = (
            short_term.recent_interests
            + short_term.recent_applications
            + short_term.recent_goals
        )
        category_counts: dict[str, int] = defaultdict(int)
        for entry in all_entries:
            category_counts[entry.category] += entry.occurrence_count

        for category, count in category_counts.items():
            if count >= _PROMOTION_THRESHOLD:
                await self.update_long_term(
                    user_id,
                    preference=category,
                    category=category,
                )

    @staticmethod
    def _upsert_entry(
        entries: list[MemoryEntry],
        key: str,
        category: str,
        now: datetime,
    ) -> list[MemoryEntry]:
        """Add or strengthen an entry in the memory list."""
        for entry in entries:
            if entry.key == key:
                return [
                    MemoryEntry(
                        key=entry.key,
                        signal_strength=min(1.0, entry.signal_strength + 0.15),
                        occurrence_count=entry.occurrence_count + 1,
                        last_seen=now,
                        category=category or entry.category,
                    )
                    if e.key == key else e
                    for e in entries
                ]
        new_entry = MemoryEntry(
            key=key,
            signal_strength=0.5,
            occurrence_count=1,
            last_seen=now,
            category=category,
        )
        entries = entries + [new_entry]
        # Keep only the most recent entries
        entries.sort(key=lambda e: e.last_seen, reverse=True)
        return entries[:_SHORT_TERM_MAX_ENTRIES]

    @staticmethod
    def _decay_entries(
        entries: list[MemoryEntry],
        now: datetime,
        half_life_days: float,
    ) -> list[MemoryEntry]:
        """Apply exponential decay and prune weak entries."""
        result: list[MemoryEntry] = []
        for entry in entries:
            last_seen = entry.last_seen
            if last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=timezone.utc)
            age_days = max(0.0, (now - last_seen).total_seconds() / 86400)
            decay_factor = pow(0.5, age_days / half_life_days)
            decayed_strength = entry.signal_strength * decay_factor
            if decayed_strength >= 0.01:
                result.append(
                    MemoryEntry(
                        key=entry.key,
                        signal_strength=round(decayed_strength, 4),
                        occurrence_count=entry.occurrence_count,
                        last_seen=entry.last_seen,
                        category=entry.category,
                    )
                )
        return result

    @staticmethod
    def _category_signal(
        entries: list[MemoryEntry],
        job_category: str,
        job_keywords: set[str],
        now: datetime,
        half_life_days: float,
    ) -> float:
        """Compute signal strength for a job category from memory entries."""
        if not entries:
            return 0.0
        total_signal = 0.0
        match_count = 0
        for entry in entries:
            is_category_match = entry.category == job_category
            is_keyword_match = any(kw in entry.key.lower() for kw in job_keywords) if job_keywords else False
            if is_category_match or is_keyword_match:
                total_signal += entry.signal_strength
                match_count += 1
        if match_count == 0:
            return 0.0
        return round(min(1.0, total_signal / max(1, match_count)), 4)
