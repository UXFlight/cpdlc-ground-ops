from __future__ import annotations
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, wait
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
        connected_pilots: list[PilotBenchmarkClient] = []
        has_responder = False
        message_phase_started = False
        admission_state: dict[str, Any] = {}

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
                    can_respond=False,
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

            admission_timeout_s = self._admission_timeout_s(config)

            admission_state = self._connect_and_wait_for_admission(
                controllers=controllers,
                pilots=pilots,
                server_url=config.server_url,
                expected_atc=config.atc,
                expected_pilots=config.pilots,
                timeout_s=admission_timeout_s,
            )

            self._select_responder(controllers)

            connected_pilots = [pilot for pilot in pilots if pilot.connected]
            has_responder = any(
                controller.connected and controller.can_respond
                for controller in controllers
            )

            if connected_pilots and has_responder:
                message_phase_started = True
                self._run_message_phase(
                    pilots=connected_pilots,
                    duration_s=config.duration_s,
                    interval_s=config.interval_s,
                )

            time.sleep(min(self.teardown_grace_s, 2.0))

            state = self._safe_get_state(config.server_url)
            if state is None:
                polling_issues += 1
                state = {
                    "pilot_count": sum(1 for pilot in pilots if pilot.connected),
                    "atc_count": sum(
                        1 for controller in controllers if controller.connected
                    ),
                    "validation_issues": ["state_snapshot_unavailable"],
                    "history_lengths": {},
                    "step_counts": {},
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
            step_counts = state.get("step_counts", {}) or {}
            pilot_stats = self._pilot_stats(pilots)

            server_processing = _stats_from_server_snapshot(
                metrics.get("server_processing_ms", {}) or {}
            )
            end_to_end = summarize_latency(self._latency_values(latency_tracker))

            observed_atc = int(state.get("atc_count") or 0)
            observed_pilots = int(state.get("pilot_count") or 0)
            observed_total_clients = observed_atc + observed_pilots
            requested_total_clients = config.atc + config.pilots
            total_errors = int(metrics.get("total_errors") or 0)

            full_population_observed = (
                observed_atc == config.atc
                and observed_pilots == config.pilots
            )

            has_end_to_end_samples = end_to_end.count > 0
            has_server_samples = server_processing.count > 0

            capacity_row_valid = (
                full_population_observed
                and has_end_to_end_samples
                and has_server_samples
                and total_errors == 0
                and len(validation_issues) == 0
                and polling_issues == 0
            )

            admission_ratio = (
                observed_total_clients / requested_total_clients
                if requested_total_clients > 0
                else 0.0
            )

            return MetricRow(
                label=config.label or self._default_label(config),
                test_id=config.test_id,
                requested_atc=config.atc,
                requested_pilots=config.pilots,
                observed_atc=observed_atc,
                observed_pilots=observed_pilots,
                duration_s=config.duration_s,
                interval_s=config.interval_s,
                total_messages=int(metrics.get("total_messages") or 0),
                total_errors=total_errors,
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
                    "connected_controllers": sum(
                        1 for controller in controllers if controller.connected
                    ),
                    "connected_pilots": sum(
                        1 for pilot in pilots if pilot.connected
                    ),
                    "responder_connected": has_responder,
                    "message_phase_started": message_phase_started,
                    "pilot_completed_cycles_min": self._min_completed_cycles(pilots),
                    "pilot_completed_cycles_max": self._max_completed_cycles(pilots),
                    "pilot_history_length_min": int(history_lengths.get("min") or 0),
                    "pilot_history_length_max": int(history_lengths.get("max") or 0),
                    "pilot_history_length_mean": float(
                        history_lengths.get("mean") or 0.0
                    ),
                    "pilot_step_count_min": int(step_counts.get("min") or 0),
                    "pilot_step_count_max": int(step_counts.get("max") or 0),
                    "pilot_step_count_mean": float(step_counts.get("mean") or 0.0),
                    "pilot_stats": pilot_stats,
                    "admission_state": admission_state,
                    "admission_complete": full_population_observed,
                    "requested_total_clients": requested_total_clients,
                    "observed_total_clients": observed_total_clients,
                    "admission_ratio": admission_ratio,
                    "drop_ratio": 1.0 - admission_ratio,
                    "full_population_observed": full_population_observed,
                    "has_end_to_end_samples": has_end_to_end_samples,
                    "has_server_samples": has_server_samples,
                    "capacity_row_valid": capacity_row_valid,
                },
            )

        finally:
            self._disable_responders(controllers)
            time.sleep(0.25)

            self._disconnect_clients([*controllers, *pilots])
            time.sleep(min(self.teardown_grace_s, 1.0))

            try:
                self._post_json(config.server_url, "/testing/benchmark/reset")
            except Exception:
                pass

            self._wait_until_clean(config.server_url, timeout_s=3.0)

    def _admission_timeout_s(self, config: BenchmarkConfig) -> float:
        return max(self.connect_timeout_s, min(config.duration_s, 60.0))

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

    def _connect_and_wait_for_admission(
        self,
        controllers: list[ControllerBenchmarkClient],
        pilots: list[PilotBenchmarkClient],
        server_url: str,
        expected_atc: int,
        expected_pilots: int,
        timeout_s: float,
    ) -> dict[str, Any]:
        started_at = time.monotonic()
        deadline = started_at + timeout_s

        clients = self._interleave_clients(controllers, pilots)
        pending = list(clients)

        attempted_clients = 0
        last_state: dict[str, Any] = {}
        admission_complete = False

        while pending and time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break

            batch_size = min(self.max_connect_workers, len(pending))
            batch = pending[:batch_size]
            pending = pending[batch_size:]
            attempted_clients += len(batch)

            self._connect_batch_bounded(
                clients=batch,
                timeout_s=min(remaining, self.connect_timeout_s),
            )

            state = self._safe_get_state(server_url)
            if state is not None:
                last_state = state

                observed_atc = int(state.get("atc_count") or 0)
                observed_pilots = int(state.get("pilot_count") or 0)

                if observed_atc >= expected_atc and observed_pilots >= expected_pilots:
                    admission_complete = True
                    break

            time.sleep(0.05)

        final_state = self._safe_get_state(server_url)
        if final_state is not None:
            last_state = final_state

        observed_atc = int(last_state.get("atc_count") or 0)
        observed_pilots = int(last_state.get("pilot_count") or 0)

        elapsed_s = time.monotonic() - started_at
        requested_total = expected_atc + expected_pilots
        observed_total = observed_atc + observed_pilots

        return {
            "admission_complete": admission_complete,
            "admission_timeout_s": timeout_s,
            "admission_elapsed_s": elapsed_s,
            "attempted_clients": attempted_clients,
            "pending_clients": len(pending),
            "requested_atc": expected_atc,
            "requested_pilots": expected_pilots,
            "requested_total_clients": requested_total,
            "observed_atc_at_admission": observed_atc,
            "observed_pilots_at_admission": observed_pilots,
            "observed_total_clients_at_admission": observed_total,
            "admission_ratio_at_admission": (
                observed_total / requested_total if requested_total > 0 else 0.0
            ),
            "state": last_state,
        }

    def _interleave_clients(
        self,
        controllers: list[ControllerBenchmarkClient],
        pilots: list[PilotBenchmarkClient],
    ) -> list[Any]:
        clients: list[Any] = []
        max_len = max(len(controllers), len(pilots))

        for index in range(max_len):
            if index < len(controllers):
                clients.append(controllers[index])
            if index < len(pilots):
                clients.append(pilots[index])

        return clients

    def _connect_batch_bounded(self, clients: list[Any], timeout_s: float) -> None:
        if not clients:
            return

        workers = min(self.max_connect_workers, len(clients))
        executor = ThreadPoolExecutor(max_workers=workers)

        try:
            futures = [
                executor.submit(client.connect, self.connect_timeout_s)
                for client in clients
            ]

            done, not_done = wait(futures, timeout=timeout_s)

            for future in done:
                try:
                    future.result()
                except Exception:
                    pass

            for future in not_done:
                future.cancel()

        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _select_responder(self, controllers: list[ControllerBenchmarkClient]) -> None:
        for controller in controllers:
            controller.can_respond = False

        for controller in controllers:
            if controller.connected:
                controller.can_respond = True
                return

    def _disable_responders(
        self,
        controllers: list[ControllerBenchmarkClient],
    ) -> None:
        for controller in controllers:
            try:
                controller.can_respond = False
            except Exception:
                pass

    def _disconnect_clients(self, clients: list[Any]) -> None:
        if not clients:
            return

        workers = min(self.max_connect_workers, len(clients))
        executor = ThreadPoolExecutor(max_workers=workers)

        try:
            futures = [
                executor.submit(self._safe_disconnect_client, client)
                for client in clients
            ]

            done, not_done = wait(
                futures,
                timeout=min(self.teardown_grace_s, 3.0),
            )

            for future in done:
                try:
                    future.result()
                except Exception:
                    pass

            for future in not_done:
                future.cancel()

        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _safe_disconnect_client(self, client: Any) -> None:
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
        with urllib.request.urlopen(url, timeout=2.0) as response:
            return json.loads(response.read().decode("utf-8"))

    def _post_json(self, server_url: str, path: str) -> dict:
        url = f"{server_url.rstrip('/')}{path}"
        request = urllib.request.Request(
            url,
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=2.0) as response:
            return json.loads(response.read().decode("utf-8"))

    def _default_label(self, config: BenchmarkConfig) -> str:
        return (
            f"{config.atc} ATC, {config.pilots} pilots, "
            f"{config.interval_s:g}s interval"
        )

    def _pilot_stats(self, pilots: list[PilotBenchmarkClient]) -> list[dict[str, Any]]:
        return [
            {
                "client_id": getattr(pilot, "client_id", "unknown"),
                "connected": bool(getattr(pilot, "connected", False)),
                "completed_cycles": int(getattr(pilot, "completed_cycles", 0)),
                "unexpected_events": list(
                    getattr(pilot, "unexpected_events", []) or []
                ),
                "errors": list(getattr(pilot, "errors", []) or []),
            }
            for pilot in pilots
        ]

    def _latency_values(self, latency_tracker: ClientLatencyTracker) -> list[float]:
        values_method = getattr(latency_tracker, "values", None)

        if callable(values_method):
            return list(values_method())

        return list(getattr(latency_tracker, "completed_ms", []))

    def _min_completed_cycles(self, pilots: list[PilotBenchmarkClient]) -> int:
        if not pilots:
            return 0
        return min(pilot.completed_cycles for pilot in pilots)

    def _max_completed_cycles(self, pilots: list[PilotBenchmarkClient]) -> int:
        if not pilots:
            return 0
        return max(pilot.completed_cycles for pilot in pilots)