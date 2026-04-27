
from app.testing.benchmark.checks.state_consistency import StateConsistencyChecks
from app.testing.benchmark.defaults import TEST_TITLES
from app.testing.benchmark.models import BenchmarkConfig, BenchmarkResult

class StateConsistencyTest:
    test_id = "R2"
    title = TEST_TITLES["R2"]

    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.checks = StateConsistencyChecks()

    def folder_suffix(self) -> str | None:
        return None

    def run(self, runner) -> BenchmarkResult:
        folder = runner.create_run_folder(self.config, self.title, self.folder_suffix())
        row = runner.execute_once(self.config)
        checks = self.checks.run(row)

        notes = []
        if not all(check.passed for check in checks):
            notes.append("This run should not be used as evidence of state consistency.")

        return BenchmarkResult(
            test_id="R2",
            title=self.title,
            run_folder=folder,
            rows=[row],
            checks=checks,
            notes=notes,
        )

    def write_extra_outputs(self, result: BenchmarkResult) -> None:
        return