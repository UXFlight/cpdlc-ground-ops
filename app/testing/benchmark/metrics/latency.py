from dataclasses import dataclass, field
from threading import Lock
from time import perf_counter_ns


@dataclass
class ClientLatencyTracker:
    pending: dict[str, int] = field(default_factory=dict)
    completed_ms: list[float] = field(default_factory=list)
    completed_ids: set[str] = field(default_factory=set)
    unmatched_receives: int = 0
    duplicate_receives: int = 0
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def mark_sent(self, message_id: str) -> None:
        with self._lock:
            self.pending[message_id] = perf_counter_ns()

    def mark_received_once(self, message_id: str) -> None:
        with self._lock:
            if message_id in self.completed_ids:
                self.duplicate_receives += 1
                return

            start_ns = self.pending.pop(message_id, None)

            if start_ns is None:
                self.unmatched_receives += 1
                return

            elapsed_ms = (perf_counter_ns() - start_ns) / 1_000_000.0
            self.completed_ids.add(message_id)
            self.completed_ms.append(elapsed_ms)

    def values(self) -> list[float]:
        with self._lock:
            return list(self.completed_ms)

    def reset(self) -> None:
        with self._lock:
            self.pending.clear()
            self.completed_ms.clear()
            self.completed_ids.clear()
            self.unmatched_receives = 0
            self.duplicate_receives = 0