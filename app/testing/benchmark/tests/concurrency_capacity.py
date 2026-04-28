from app.testing.benchmark.defaults import R3_LOAD_POINTS, TEST_TITLES
from app.testing.benchmark.models import BenchmarkConfig, BenchmarkResult, CheckResult
from app.testing.benchmark.output.plots import PlotWriter

class ConcurrencyCapacityTest:
    test_id = "R3"
    title = TEST_TITLES["R3"]

    def __init__(self, config: BenchmarkConfig, use_ladder: bool = True):
        self.config = config
        self.use_ladder = use_ladder
        self.plots = PlotWriter()

    def folder_suffix(self) -> str | None:
        return "load_ladder" if self.use_ladder else None

    def run(self, runner) -> BenchmarkResult:
        folder = runner.create_run_folder(self.config, self.title, self.folder_suffix())

        load_points = R3_LOAD_POINTS if self.use_ladder else [(self.config.atc, self.config.pilots)]
        rows = []
        stopped_at_invalid_row = False

        for atc, pilots in load_points:
            run_config = BenchmarkConfig(
                test_id="R3",
                server_url=self.config.server_url,
                atc=atc,
                pilots=pilots,
                duration_s=self.config.duration_s,
                interval_s=self.config.interval_s,
                label=f"{atc} ATC, {pilots} pilots",
            )

            row = runner.execute_once(run_config)
            rows.append(row)

            if not row.details.get("capacity_row_valid", False):
                stopped_at_invalid_row = True
                break

        valid_rows = [
            row for row in rows
            if row.details.get("capacity_row_valid", False)
        ]

        invalid_rows = [
            row for row in rows
            if not row.details.get("capacity_row_valid", False)
        ]

        checks = [
            CheckResult(
                name="at_least_one_valid_capacity_point",
                passed=len(valid_rows) > 0,
                details=f"valid_rows={len(valid_rows)}; total_rows={len(rows)}",
            ),
            CheckResult(
                name="all_reported_capacity_points_valid",
                passed=len(invalid_rows) == 0,
                details=self._format_invalid_rows(invalid_rows),
            ),
        ]

        notes = []
        if stopped_at_invalid_row:
            notes.append(
                "R3 stopped at the first invalid capacity point. "
                "Rows after this point should be evaluated under overload/admission behavior rather than R3 latency-capacity behavior."
            )

        return BenchmarkResult(
            test_id="R3",
            title=self.title,
            run_folder=folder,
            rows=rows,
            checks=checks,
            notes=notes,
        )

    def write_extra_outputs(self, result: BenchmarkResult) -> None:
        self.plots.write_r3_end_to_end_plot(result.run_folder, result.rows)
        self.plots.write_r3_server_processing_plot(result.run_folder, result.rows)

    def _format_invalid_rows(self, rows) -> str:
        if not rows:
            return "all rows valid"

        return "; ".join(
            (
                f"{row.label}: requested={row.requested_atc}/{row.requested_pilots}, "
                f"observed={row.observed_atc}/{row.observed_pilots}, "
                f"e2e_count={row.end_to_end_latency.count}, "
                f"errors={row.total_errors}, "
                f"polling_issues={row.polling_issues}, "
                f"validation_issues={row.validation_issues}"
            )
            for row in rows
        )