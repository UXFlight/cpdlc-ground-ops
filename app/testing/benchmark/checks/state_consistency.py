from app.testing.benchmark.models import CheckResult, MetricRow

class StateConsistencyChecks:
    def run(self, row: MetricRow) -> list[CheckResult]:
        return [
            self.population_integrity(row),
            self.no_server_errors(row),
            self.no_validation_issues(row),
            self.no_polling_issues(row),
            self.no_client_errors(row),
            self.progress_observed(row),
            self.end_to_end_samples_observed(row),
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
        details = row.details.get("state_validation_issues", [])
        return CheckResult(
            "no_validation_issues",
            row.validation_issues == 0,
            f"validation_issues={row.validation_issues}; details={details}",
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

    def progress_observed(self, row: MetricRow) -> CheckResult:
        return CheckResult(
            "progress_observed",
            row.total_messages > 0,
            f"total_messages={row.total_messages}",
        )

    def end_to_end_samples_observed(self, row: MetricRow) -> CheckResult:
        return CheckResult(
            "end_to_end_samples_observed",
            row.end_to_end_latency.count > 0,
            f"end_to_end_latency_count={row.end_to_end_latency.count}",
        )