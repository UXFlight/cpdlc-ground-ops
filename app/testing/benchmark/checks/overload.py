from app.testing.benchmark.models import CheckResult, MetricRow

class OverloadChecks:
    def summarize(self, row: MetricRow) -> list[str]:
        requested_total = row.requested_total
        observed_total = row.observed_total

        admission_ratio = observed_total / requested_total if requested_total else 0.0
        drop_ratio = row.dropped_total / requested_total if requested_total else 0.0

        notes = [
            f"requested_total_clients={requested_total}",
            f"observed_total_clients={observed_total}",
            f"dropped_total_clients={row.dropped_total}",
            f"admission_ratio={admission_ratio:.4f}",
            f"drop_ratio={drop_ratio:.4f}",
            "Latency metrics are computed only from completed message exchanges.",
        ]

        if row.dropped_total > 0:
            notes.append("Some requested clients were not observed during the run.")

        if row.polling_issues > 0:
            notes.append("Polling issues were observed during the overload run.")

        if row.validation_issues == 0:
            notes.append("No validation issues were reported.")
        else:
            notes.append("Validation issues were reported.")

        return notes

    def run(self, row: MetricRow) -> list[CheckResult]:
        return [
            CheckResult(
                "overload_run_completed",
                row.total_messages >= 0,
                f"total_messages={row.total_messages}",
            ),
            CheckResult(
                "no_validation_issues",
                row.validation_issues == 0,
                f"validation_issues={row.validation_issues}",
            ),
        ]