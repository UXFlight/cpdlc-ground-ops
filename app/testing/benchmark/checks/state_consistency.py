from __future__ import annotations
from typing import Any
from app.testing.benchmark.models import CheckResult, MetricRow

class StateConsistencyChecks:
    def run(self, row: MetricRow) -> list[CheckResult]:
        return [
            self.population_integrity(row),
            self.no_errors_or_issues(row),
            self.per_pilot_isolation(row),
            self.per_pilot_progress(row),
            self.latency_samples_observed(row),
        ]

    def population_integrity(self, row: MetricRow) -> CheckResult:
        passed = (
            row.requested_atc == row.observed_atc
            and row.requested_pilots == row.observed_pilots
        )

        details = (
            f"requested ATC/pilots={row.requested_atc}/{row.requested_pilots}; "
            f"observed ATC/pilots={row.observed_atc}/{row.observed_pilots}"
        )

        return CheckResult("population_integrity", passed, details)

    def no_errors_or_issues(self, row: MetricRow) -> CheckResult:
        client_error_count = int(row.details.get("client_error_count", 0))
        unexpected_pilot_event_count = int(
            row.details.get("unexpected_pilot_event_count", 0)
        )
        unmatched_receives = int(row.details.get("latency_unmatched_receives", 0))
        duplicate_receives = int(row.details.get("latency_duplicate_receives", 0))

        passed = (
            row.total_errors == 0
            and row.validation_issues == 0
            and row.polling_issues == 0
            and client_error_count == 0
            and unexpected_pilot_event_count == 0
            and unmatched_receives == 0
            and duplicate_receives == 0
        )

        details = (
            f"total_errors={row.total_errors}; "
            f"validation_issues={row.validation_issues}; "
            f"polling_issues={row.polling_issues}; "
            f"client_error_count={client_error_count}; "
            f"unexpected_pilot_event_count={unexpected_pilot_event_count}; "
            f"latency_unmatched_receives={unmatched_receives}; "
            f"latency_duplicate_receives={duplicate_receives}"
        )

        return CheckResult("no_errors_or_issues", passed, details)

    def per_pilot_isolation(self, row: MetricRow) -> CheckResult:
        pilots = self._pilot_stats(row)

        if not pilots:
            return CheckResult(
                "per_pilot_isolation",
                False,
                "missing pilot_stats; cannot verify per-pilot isolation",
            )

        unexpected_by_pilot: dict[str, list[Any]] = {}

        for pilot in pilots:
            client_id = str(pilot.get("client_id", "unknown"))
            unexpected_events = pilot.get("unexpected_events", [])

            if unexpected_events:
                unexpected_by_pilot[client_id] = list(unexpected_events)

        passed = len(unexpected_by_pilot) == 0

        details = (
            f"pilots_checked={len(pilots)}; "
            f"unexpected_events={unexpected_by_pilot}"
        )

        return CheckResult("per_pilot_isolation", passed, details)

    def per_pilot_progress(self, row: MetricRow) -> CheckResult:
        pilots = self._pilot_stats(row)

        if not pilots:
            return CheckResult(
                "per_pilot_progress",
                False,
                "missing pilot_stats; cannot verify per-pilot progress",
            )

        min_cycles_required = 1
        completed_cycles: dict[str, int] = {}
        failed: dict[str, int] = {}

        for pilot in pilots:
            client_id = str(pilot.get("client_id", "unknown"))
            cycles = int(pilot.get("completed_cycles", 0))
            completed_cycles[client_id] = cycles

            if cycles < min_cycles_required:
                failed[client_id] = cycles

        min_observed = min(completed_cycles.values()) if completed_cycles else 0
        max_observed = max(completed_cycles.values()) if completed_cycles else 0

        passed = (
            len(pilots) == row.requested_pilots
            and len(failed) == 0
        )

        details = (
            f"requested_pilots={row.requested_pilots}; "
            f"pilots_checked={len(pilots)}; "
            f"min_cycles_required={min_cycles_required}; "
            f"min_completed_cycles={min_observed}; "
            f"max_completed_cycles={max_observed}; "
            f"failed={failed}"
        )

        return CheckResult("per_pilot_progress", passed, details)

    def latency_samples_observed(self, row: MetricRow) -> CheckResult:
        passed = (
            row.end_to_end_latency.count > 0
            and row.server_processing_latency.count > 0
        )

        details = (
            f"end_to_end_latency_count={row.end_to_end_latency.count}; "
            f"server_processing_latency_count={row.server_processing_latency.count}"
        )

        return CheckResult("latency_samples_observed", passed, details)

    def _pilot_stats(self, row: MetricRow) -> list[dict[str, Any]]:
        pilots = row.details.get("pilot_stats", [])

        if not isinstance(pilots, list):
            return []

        return [pilot for pilot in pilots if isinstance(pilot, dict)]