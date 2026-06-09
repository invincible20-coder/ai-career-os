"""
Async event bus used for real execution transparency streams.
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

class EventBus:
    """Per-process pub/sub bus with SSE framing and heartbeat support."""

    def __init__(self, *, queue_size: int = 250):
        self.channels: dict[str, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)
        self.queue_size = queue_size
        self._lock = asyncio.Lock()

    async def subscribe(self, channel: str) -> AsyncGenerator[str, None]:
        """Subscribe to a channel and yield SSE formatted strings."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=self.queue_size)
        async with self._lock:
            self.channels[channel].add(queue)
        await queue.put(self._envelope("stream_connected", channel, {"message": "connected"}))

        try:
            while True:
                try:
                    event_data = await asyncio.wait_for(queue.get(), timeout=20)
                except asyncio.TimeoutError:
                    event_data = self._envelope("heartbeat", channel, {})
                yield self._format_sse(event_data)
        except asyncio.CancelledError:
            return
        finally:
            async with self._lock:
                self.channels[channel].discard(queue)
                if not self.channels[channel]:
                    del self.channels[channel]

    async def publish(self, channel: str, event_data: dict) -> None:
        """Publish an event to all subscribers of a channel."""
        event = self._envelope(
            event_data.get("type") or event_data.get("event") or "event",
            channel,
            event_data,
        )
        async with self._lock:
            subscribers = list(self.channels.get(channel, set()))
        for queue in subscribers:
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            await queue.put(event)

    async def publish_many(self, channels: list[str], event_data: dict) -> None:
        for channel in channels:
            await self.publish(channel, event_data)

    @staticmethod
    def _envelope(event_type: str, channel: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": event_type,
            "channel": channel,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "payload": payload,
        }

    @staticmethod
    def _format_sse(event: dict[str, Any]) -> str:
        event_type = str(event.get("type", "event"))
        return f"event: {event_type}\ndata: {json.dumps(event, default=str)}\n\n"


# Compatibility fallback for older code paths. The FastAPI app uses app.state.event_bus.
event_bus = EventBus()
