"""
Optional Redis cache facade with deterministic in-process fallback.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class CacheClient:
    """Async cache interface used for sessions, streaming state, and throttling helpers."""

    redis_url: str | None = None
    enabled: bool = False
    _redis: Any = None
    _fallback: dict[str, tuple[Any, float | None]] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def connect(self) -> None:
        if not self.enabled or not self.redis_url:
            return
        try:
            from redis.asyncio import Redis

            self._redis = Redis.from_url(self.redis_url, decode_responses=True)
            await self._redis.ping()
        except Exception:
            self._redis = None

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()

    async def get(self, key: str) -> Any:
        if self._redis is not None:
            return await self._redis.get(key)
        async with self._lock:
            value = self._fallback.get(key)
            if value is None:
                return None
            payload, expires_at = value
            if expires_at is not None and expires_at <= time.time():
                self._fallback.pop(key, None)
                return None
            return payload

    async def set(self, key: str, value: Any, *, ttl_seconds: int | None = None) -> None:
        if self._redis is not None:
            await self._redis.set(key, value, ex=ttl_seconds)
            return
        expires_at = time.time() + ttl_seconds if ttl_seconds else None
        async with self._lock:
            self._fallback[key] = (value, expires_at)

    async def delete(self, key: str) -> None:
        if self._redis is not None:
            await self._redis.delete(key)
            return
        async with self._lock:
            self._fallback.pop(key, None)
