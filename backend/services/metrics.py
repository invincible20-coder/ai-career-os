"""
Small in-process observability collector for request and execution metrics.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from time import perf_counter


@dataclass(slots=True)
class MetricsCollector:
    """Aggregates lightweight metrics without adding a hard runtime dependency."""

    request_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    status_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    latency_ms_total: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    event_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def timer(self) -> float:
        return perf_counter()

    def observe_request(self, *, path: str, method: str, status_code: int, started_at: float) -> None:
        key = f"{method} {path}"
        self.request_counts[key] += 1
        self.status_counts[str(status_code)] += 1
        self.latency_ms_total[key] += (perf_counter() - started_at) * 1000

    def increment_event(self, event_name: str) -> None:
        self.event_counts[event_name] += 1

    def snapshot(self) -> dict[str, object]:
        average_latency = {
            key: round(self.latency_ms_total[key] / max(count, 1), 2)
            for key, count in self.request_counts.items()
        }
        return {
            "requests": dict(self.request_counts),
            "statuses": dict(self.status_counts),
            "average_latency_ms": average_latency,
            "events": dict(self.event_counts),
        }
