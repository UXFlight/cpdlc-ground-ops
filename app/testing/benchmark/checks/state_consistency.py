from __future__ import annotations
from typing import Any
from app.testing.benchmark.models import CheckResult, MetricRow
from app.utils.constants import DEFAULT_STEPS

EXPECTED_STEP_COUNT = len(DEFAULT_STEPS)

class StateConsistencyChecks:
    def run(self, row: MetricRow) -> list[CheckResult]:
        return [
            self.population_integrity(row),
            self.no_server_errors(row),
            self.no_validation_issues(row),
            self.no_polling_issues(row),
            self.no_client_errors(row),
            self.no_unmatched_latency_events(row),
            self.per_pilot_isolation(row),
            self.progress_guarantee(row),
            self.bounded_state_growth(row),
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

    def no_server_errors(self, row: MetricRow) -> CheckResult:
        return CheckResult(
            "no_server_errors",
            row.total_errors == 0,
            f"total_errors={row.total_errors}",
        )

    def no_validation_issues(self, row: MetricRow) -> CheckResult:
        issues = row.details.get("state_validation_issues", [])

        return CheckResult(
            "no_validation_issues",
            row.validation_issues == 0,
            f"validation_issues={row.validation_issues}; details={issues}",
        )

    def no_polling_issues(self, row: MetricRow) -> CheckResult:
        return CheckResult(
            "no_polling_issues",
            row.polling_issues == 0,
            f"polling_issues={row.polling_issues}",
        )

    def no_client_errors(self, row: MetricRow) -> CheckResult:
        count = int(row.details.get("client_error_count", 0))
        examples = row.details.get("client_error_examples", [])

        return CheckResult(
            "no_client_errors",
            count == 0,
            f"client_error_count={count}; examples={examples}",
        )

    def no_unmatched_latency_events(self, row: MetricRow) -> CheckResult:
        unmatched = int(row.details.get("latency_unmatched_receives", 0))
        duplicates = int(row.details.get("latency_duplicate_receives", 0))

        passed = unmatched == 0

        details = (
            f"latency_unmatched_receives={unmatched}; "
            f"latency_duplicate_receives={duplicates}; "
            "duplicate receives are reported but not treated as a failure because "
            "ATC-room broadcasts are intentionally received by multiple ATC clients"
        )

        return CheckResult("no_unmatched_latency_events", passed, details)

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

    def progress_guarantee(self, row: MetricRow) -> CheckResult:
        pilots = self._pilot_stats(row)

        if not pilots:
            return CheckResult(
                "progress_guarantee",
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

        return CheckResult("progress_guarantee", passed, details)

    def bounded_state_growth(self, row: MetricRow) -> CheckResult:
        step_min = int(row.details.get("pilot_step_count_min", 0))
        step_max = int(row.details.get("pilot_step_count_max", 0))
        step_mean = float(row.details.get("pilot_step_count_mean", 0.0))

        passed = (
            step_min == EXPECTED_STEP_COUNT
            and step_max == EXPECTED_STEP_COUNT
        )

        details = (
            f"expected_step_count={EXPECTED_STEP_COUNT}; "
            f"step_count_min={step_min}; "
            f"step_count_max={step_max}; "
            f"step_count_mean={step_mean:.2f}"
        )

        return CheckResult("bounded_state_growth", passed, details)

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