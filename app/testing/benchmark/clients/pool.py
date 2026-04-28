from __future__ import annotations
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Any
from app.testing.benchmark.clients.controller import ControllerBenchmarkClient
from app.testing.benchmark.clients.pilot import PilotBenchmarkClient
from app.testing.benchmark.defaults import (
    CONNECT_TIMEOUT_S,
    MAX_CONNECT_WORKERS,
    POLL_INTERVAL_S,
    TEARDOWN_GRACE_S,
)
from app.testing.benchmark.metrics.latency import ClientLatencyTracker
from app.testing.benchmark.metrics.summary import summarize_latency
from app.testing.benchmark.models import BenchmarkConfig, LatencyStats, MetricRow

class MessageIdFactory:
    def __init__(self, test_id: str) -> None:
        self.test_id = test_id
        self._counter = 0
        self._lock = Lock()

    def new(self, prefix: str) -> str:
        with self._lock:
            self._counter += 1
            return f"{self.test_id}-{prefix}-{self._counter}"


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)

def _stats_from_server_snapshot(data: dict) -> LatencyStats:
    return LatencyStats(
        count=int(data.get("count") or 0),
        p50_ms=_float_or_none(data.get("p50_ms")),
        p95_ms=_float_or_none(data.get("p95_ms")),
        mean_ms=_float_or_none(data.get("mean_ms")),
        min_ms=_float_or_none(data.get("min_ms")),
        max_ms=_float_or_none(data.get("max_ms")),
    )

class ClientPool:
    def __init__(self) -> None:
        self.poll_interval_s = POLL_INTERVAL_S
        self.connect_timeout_s = CONNECT_TIMEOUT_S
        self.teardown_grace_s = TEARDOWN_GRACE_S
        self.max_connect_workers = MAX_CONNECT_WORKERS

    def execute(self, config: BenchmarkConfig) -> MetricRow:
        latency_tracker = ClientLatencyTracker()
        message_ids = MessageIdFactory(config.test_id)
        polling_issues = 0

        controllers: list[ControllerBenchmarkClient] = []
        pilots: list[PilotBenchmarkClient] = []
        try:
            try:
                self._post_json(config.server_url, "/testing/benchmark/reset")
            except Exception:
                polling_issues += 1

            clean = self._wait_until_clean(config.server_url, timeout_s=5.0)
            if not clean:
                state = self._safe_get_state(config.server_url) or {}
                raise RuntimeError(
                    "Benchmark server could not be reset to a clean state. "
                    f"Observed {state.get('atc_count', 0)} ATC and "
                    f"{state.get('pilot_count', 0)} pilots after reset."
                )

            controllers = [
                ControllerBenchmarkClient(
                    client_id=f"controller-{i + 1}",
                    server_url=config.server_url,
                    latency_tracker=latency_tracker,
                    message_id_factory=message_ids.new,
                    can_respond=(i == 0),
                )
                for i in range(config.atc)
            ]

            pilots = [
                PilotBenchmarkClient(
                    client_id=f"pilot-{i + 1}",
                    server_url=config.server_url,
                    latency_tracker=latency_tracker,
                    message_id_factory=message_ids.new,
                )
                for i in range(config.pilots)
            ]

            self._connect_clients(controllers)
            self._connect_clients(pilots)

            self._wait_for_admission(
                server_url=config.server_url,
                expected_atc=config.atc,
                expected_pilots=config.pilots,
                timeout_s=self.connect_timeout_s,
            )

            self._run_message_phase(
                pilots=[pilot for pilot in pilots if pilot.connected],
                duration_s=config.duration_s,
                interval_s=config.interval_s,
            )

            time.sleep(min(self.teardown_grace_s, 2.0))

            state = self._safe_get_state(config.server_url)
            if state is None:
                polling_issues += 1
                state = {
                    "pilot_count": sum(1 for pilot in pilots if pilot.connected),
                    "atc_count": sum(1 for controller in controllers if controller.connected),
                    "validation_issues": ["state_snapshot_unavailable"],
                    "history_lengths": {},
                }

            metrics = self._safe_get_metrics(config.server_url)
            if metrics is None:
                polling_issues += 1
                metrics = {
                    "total_messages": 0,
                    "total_errors": 0,
                    "server_processing_ms": {},
                }

            client_errors: list[Any] = []
            for controller in controllers:
                client_errors.extend(controller.errors)
            for pilot in pilots:
                client_errors.extend(pilot.errors)

            unexpected_events: list[Any] = []
            for pilot in pilots:
                unexpected_events.extend(getattr(pilot, "unexpected_events", []))

            validation_issues = list(state.get("validation_issues", []) or [])
            history_lengths = state.get("history_lengths", {}) or {}

            server_processing = _stats_from_server_snapshot(
                metrics.get("server_processing_ms", {}) or {}
            )
            end_to_end = summarize_latency(latency_tracker.values())

            return MetricRow(
                label=config.label or self._default_label(config),
                test_id=config.test_id,
                requested_atc=config.atc,
                requested_pilots=config.pilots,
                observed_atc=int(state.get("atc_count") or 0),
                observed_pilots=int(state.get("pilot_count") or 0),
                duration_s=config.duration_s,
                interval_s=config.interval_s,
                total_messages=int(metrics.get("total_messages") or 0),
                total_errors=int(metrics.get("total_errors") or 0),
                validation_issues=len(validation_issues),
                polling_issues=polling_issues,
                end_to_end_latency=end_to_end,
                server_processing_latency=server_processing,
                details={
                    "state_validation_issues": validation_issues,
                    "client_error_count": len(client_errors),
                    "client_error_examples": client_errors[:10],
                    "unexpected_pilot_event_count": len(unexpected_events),
                    "unexpected_pilot_event_examples": unexpected_events[:10],
                    "latency_unmatched_receives": latency_tracker.unmatched_receives,
                    "latency_duplicate_receives": latency_tracker.duplicate_receives,
                    "connected_controllers": sum(1 for controller in controllers if controller.connected),
                    "connected_pilots": sum(1 for pilot in pilots if pilot.connected),
                    "pilot_completed_cycles_min": self._min_completed_cycles(pilots),
                    "pilot_completed_cycles_max": self._max_completed_cycles(pilots),
                    "pilot_history_length_min": int(history_lengths.get("min") or 0),
                    "pilot_history_length_max": int(history_lengths.get("max") or 0),
                    "pilot_history_length_mean": float(history_lengths.get("mean") or 0.0),
                },
            )

        finally:
            self._disconnect_clients(pilots)
            self._disconnect_clients(controllers)

            # Give Flask-SocketIO time to process disconnect events before the next R3 load point.
            time.sleep(1.0)

            # Best-effort cleanup. The next run also calls /reset before starting.
            self._wait_until_clean(config.server_url, timeout_s=3.0)

    def _run_message_phase(
        self,
        pilots: list[PilotBenchmarkClient],
        duration_s: float,
        interval_s: float,
    ) -> None:
        end_time = time.monotonic() + duration_s

        while time.monotonic() < end_time:
            for pilot in pilots:
                if pilot.is_ready():
                    pilot.send_request()

            remaining = end_time - time.monotonic()
            if remaining <= 0:
                break

            time.sleep(min(interval_s, remaining))

    def _connect_clients(self, clients: list[Any]) -> None:
        if not clients:
            return

        workers = min(self.max_connect_workers, len(clients))

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(client.connect, self.connect_timeout_s)
                for client in clients
            ]

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:
                    pass

    def _disconnect_clients(self, clients: list[Any]) -> None:
        for client in clients:
            try:
                client.disconnect()
            except Exception:
                pass

    def _wait_until_clean(self, server_url: str, timeout_s: float) -> bool:
        deadline = time.monotonic() + timeout_s

        while time.monotonic() < deadline:
            state = self._safe_get_state(server_url)

            if state is not None:
                atc_count = int(state.get("atc_count") or 0)
                pilot_count = int(state.get("pilot_count") or 0)

                if atc_count == 0 and pilot_count == 0:
                    return True

            time.sleep(0.25)

        return False

    def _wait_for_admission(
        self,
        server_url: str,
        expected_atc: int,
        expected_pilots: int,
        timeout_s: float,
    ) -> dict:
        deadline = time.monotonic() + timeout_s
        last_state: dict = {}

        while time.monotonic() < deadline:
            state = self._safe_get_state(server_url)
            if state is not None:
                last_state = state

                if (
                    int(state.get("atc_count") or 0) >= expected_atc
                    and int(state.get("pilot_count") or 0) >= expected_pilots
                ):
                    return state

            time.sleep(self.poll_interval_s)

        return last_state

    def _safe_get_state(self, server_url: str) -> dict | None:
        try:
            return self._get_json(server_url, "/testing/benchmark/state")
        except Exception:
            return None

    def _safe_get_metrics(self, server_url: str) -> dict | None:
        try:
            return self._get_json(server_url, "/testing/benchmark/metrics")
        except Exception:
            return None

    def _get_json(self, server_url: str, path: str) -> dict:
        url = f"{server_url.rstrip('/')}{path}"
        with urllib.request.urlopen(url, timeout=5.0) as response:
            return json.loads(response.read().decode("utf-8"))

    def _post_json(self, server_url: str, path: str) -> dict:
        url = f"{server_url.rstrip('/')}{path}"
        request = urllib.request.Request(
            url,
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=5.0) as response:
            return json.loads(response.read().decode("utf-8"))

    def _default_label(self, config: BenchmarkConfig) -> str:
        return f"{config.atc} ATC, {config.pilots} pilots, {config.interval_s:g}s interval"

    def _min_completed_cycles(self, pilots: list[PilotBenchmarkClient]) -> int:
        if not pilots:
            return 0
        return min(pilot.completed_cycles for pilot in pilots)

    def _max_completed_cycles(self, pilots: list[PilotBenchmarkClient]) -> int:
        if not pilots:
            return 0
        return max(pilot.completed_cycles for pilot in pilots)