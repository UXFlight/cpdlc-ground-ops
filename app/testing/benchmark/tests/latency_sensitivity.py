from app.testing.benchmark.defaults import R1_INTERVALS, TEST_TITLES
from app.testing.benchmark.models import BenchmarkConfig, BenchmarkResult
from app.testing.benchmark.output.plots import PlotWriter

class LatencySensitivityTest:
    test_id = "R1"
    title = TEST_TITLES["R1"]

    def __init__(self, config: BenchmarkConfig, use_sweep: bool = True):
        self.config = config
        self.use_sweep = use_sweep
        self.plots = PlotWriter()

    def folder_suffix(self) -> str | None:
        return "interval_sweep" if self.use_sweep else None

    def run(self, runner) -> BenchmarkResult:
        folder = runner.create_run_folder(self.config, self.title, self.folder_suffix())

        intervals = R1_INTERVALS if self.use_sweep else [self.config.interval_s]
        rows = []

        for interval in intervals:
            run_config = BenchmarkConfig(
                test_id="R1",
                server_url=self.config.server_url,
                atc=self.config.atc,
                pilots=self.config.pilots,
                duration_s=self.config.duration_s,
                interval_s=interval,
                label=f"{interval:g}s interval",
            )

            row = runner.execute_once(run_config)
            rows.append(row)

        return BenchmarkResult(
            test_id="R1",
            title=self.title,
            run_folder=folder,
            rows=rows,
        )

    def write_extra_outputs(self, result: BenchmarkResult) -> None:
        self.plots.write_r1_latency_plot(result.run_folder, result.rows)