from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from time import perf_counter_ns
from typing import Any

from app.utils.socket_constants import ATC_ROOM


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None

    ordered = sorted(values)
    index = round((pct / 100.0) * (len(ordered) - 1))
    return ordered[index]


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


@dataclass
class LatencyRecorder:
    values_ms: list[float] = field(default_factory=list)

    def add_ms(self, value_ms: float) -> None:
        if value_ms >= 0:
            self.values_ms.append(value_ms)

    def snapshot(self) -> dict[str, float | int | None]:
        values = self.values_ms

        return {
            "count": len(values),
            "p50_ms": percentile(values, 50),
            "p95_ms": percentile(values, 95),
            "mean_ms": mean(values),
            "min_ms": min(values) if values else None,
            "max_ms": max(values) if values else None,
        }


class SystemMetrics:
    """
    Server-side benchmark metrics.

    This class measures only server-side behavior.
    End-to-end latency must be measured by benchmark clients.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self.total_messages = 0
            self.total_errors = 0
            self.role_counts: dict[str, int] = {}
            self.delivered_counts: dict[str, int] = {}
            self.server_processing_ms = LatencyRecorder()

    def start_timer(self) -> int:
        return perf_counter_ns()

    def record_message(self, role: str, start_ns: int) -> None:
        elapsed_ms = (perf_counter_ns() - start_ns) / 1_000_000.0

        with self._lock:
            self.total_messages += 1
            self.role_counts[role] = self.role_counts.get(role, 0) + 1
            self.server_processing_ms.add_ms(elapsed_ms)

    def record_emit(self, event: str, room: str | None) -> None:
        if room is None:
            return

        target = "atc_room" if room == ATC_ROOM else "pilot"

        with self._lock:
            self.delivered_counts[target] = self.delivered_counts.get(target, 0) + 1

    def record_error(self) -> None:
        with self._lock:
            self.total_errors += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_messages": self.total_messages,
                "total_errors": self.total_errors,
                "role_counts": dict(self.role_counts),
                "delivered_counts": dict(self.delivered_counts),
                "server_processing_ms": self.server_processing_ms.snapshot(),
            }