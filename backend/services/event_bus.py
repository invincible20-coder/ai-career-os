import asyncio
from typing import AsyncGenerator, Dict, Set
from collections import defaultdict
import json

class EventBus:
    def __init__(self):
        # Maps a channel (e.g., user_id or session_id) to a set of queues for connected clients
        self.channels: Dict[str, Set[asyncio.Queue]] = defaultdict(set)

    async def subscribe(self, channel: str) -> AsyncGenerator[str, None]:
        """Subscribe to a channel and yield SSE formatted strings."""
        queue = asyncio.Queue()
        self.channels[channel].add(queue)
        
        try:
            while True:
                event_data = await queue.get()
                # Yield in SSE format
                yield f"data: {json.dumps(event_data)}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            self.channels[channel].remove(queue)
            if not self.channels[channel]:
                del self.channels[channel]

    async def publish(self, channel: str, event_data: dict) -> None:
        """Publish an event to all subscribers of a channel."""
        if channel in self.channels:
            for queue in self.channels[channel]:
                await queue.put(event_data)

# Global event bus instance
event_bus = EventBus()
