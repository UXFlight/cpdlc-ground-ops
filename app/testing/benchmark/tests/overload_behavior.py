
from app.testing.benchmark.checks.overload import OverloadChecks
from app.testing.benchmark.defaults import TEST_TITLES
from app.testing.benchmark.models import BenchmarkConfig, BenchmarkResult

class OverloadBehaviorTest:
    test_id = "R4"
    title = TEST_TITLES["R4"]

    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.checks = OverloadChecks()

    def folder_suffix(self) -> str | None:
        return None

    def run(self, runner) -> BenchmarkResult:
        folder = runner.create_run_folder(self.config, self.title, self.folder_suffix())
        row = runner.execute_once(self.config)

        checks = self.checks.run(row)
        notes = self.checks.summarize(row)

        return BenchmarkResult(
            test_id="R4",
            title=self.title,
            run_folder=folder,
            rows=[row],
            checks=checks,
            notes=notes,
        )

    def write_extra_outputs(self, result: BenchmarkResult) -> None:
        return