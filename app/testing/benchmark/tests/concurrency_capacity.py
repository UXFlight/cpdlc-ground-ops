from app.testing.benchmark.defaults import R3_LOAD_POINTS, TEST_TITLES
from app.testing.benchmark.models import BenchmarkConfig, BenchmarkResult
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

        return BenchmarkResult(
            test_id="R3",
            title=self.title,
            run_folder=folder,
            rows=rows,
        )

    def write_extra_outputs(self, result: BenchmarkResult) -> None:
        self.plots.write_r3_end_to_end_plot(result.run_folder, result.rows)
        self.plots.write_r3_server_processing_plot(result.run_folder, result.rows)