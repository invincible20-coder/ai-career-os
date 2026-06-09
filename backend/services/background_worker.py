"""
Async background worker abstraction for heavy local jobs.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from backend.core.logger import get_logger

logger = get_logger(__name__)

JobCallable = Callable[[], Awaitable[None]]


@dataclass(slots=True)
class BackgroundWorker:
    """Small retry-safe queue used when Redis/RQ is unavailable in local mode."""

    max_queue_size: int = 500
    _queue: asyncio.Queue[tuple[str, JobCallable]] = field(init=False)
    _task: asyncio.Task | None = None
    _stopping: bool = False

    def __post_init__(self) -> None:
        self._queue = asyncio.Queue(maxsize=self.max_queue_size)

    async def start(self) -> None:
        self._stopping = False
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run(), name="huntai-background-worker")

    async def stop(self) -> None:
        self._stopping = True
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def enqueue(self, name: str, job: JobCallable) -> None:
        await self._queue.put((name, job))

    async def _run(self) -> None:
        while not self._stopping:
            name, job = await self._queue.get()
            try:
                await job()
                logger.info("background_job_completed", extra={"event": "background_job_completed", "job": name})
            except Exception as exc:
                logger.exception(
                    "background_job_failed",
                    extra={"event": "background_job_failed", "job": name, "reason": str(exc)},
                )
            finally:
                self._queue.task_done()
