from collections import deque
from typing import Deque, Dict, Optional, List

METRICS_WINDOW = 1000


def _percentile(values: List[float], pct: float) -> Optional[float]:
    if not values:
        return None
    sorted_vals = sorted(values)
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    rank = int(round((pct / 100.0) * (len(sorted_vals) - 1)))
    return sorted_vals[rank]


class SystemMetrics:
    def __init__(self) -> None:
        self.total_messages = 0
        self.total_errors = 0
        self.role_counts: Dict[str, int] = {}
        self.delivered_counts: Dict[str, int] = {}
        self.end_to_end_ms: Deque[float] = deque(maxlen=METRICS_WINDOW)
        self.server_processing_ms: Deque[float] = deque(maxlen=METRICS_WINDOW)

    def record_event(self, from_role: str, start_ts: float, end_ts: float,
                     client_sent_ts: Optional[float]) -> None:
        self.total_messages += 1
        self.role_counts[from_role] = self.role_counts.get(from_role, 0) + 1
        self.server_processing_ms.append((end_ts - start_ts) * 1000.0)
        if client_sent_ts is not None:
            self.end_to_end_ms.append((end_ts - client_sent_ts) * 1000.0)

    def record_emit(self, event: str, room: Optional[str]) -> None:
        if room == "atc_room":
            self.delivered_counts["atc"] = self.delivered_counts.get("atc", 0) + 1
            return
        if room:
            self.delivered_counts["pilot"] = self.delivered_counts.get("pilot", 0) + 1

    def record_error(self) -> None:
        self.total_errors += 1

    def snapshot(self) -> dict:
        end_vals = list(self.end_to_end_ms)
        server_vals = list(self.server_processing_ms)
        return {
            "total_messages": self.total_messages,
            "total_errors": self.total_errors,
            "role_counts": dict(self.role_counts),
            "delivered_counts": dict(self.delivered_counts),
            "end_to_end_ms": {
                "p50": _percentile(end_vals, 50),
                "p95": _percentile(end_vals, 95),
            },
            "server_processing_ms": {
                "p50": _percentile(server_vals, 50),
                "p95": _percentile(server_vals, 95),
            },
        }
