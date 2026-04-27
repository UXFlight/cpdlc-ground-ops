from __future__ import annotations
from pathlib import Path
from typing import Protocol
from app.testing.benchmark.clients.pool import ClientPool
from app.testing.benchmark.models import BenchmarkConfig, BenchmarkResult, MetricRow
from app.testing.benchmark.output.console import ConsolePrinter
from app.testing.benchmark.output.files import ResultFileWriter
from app.testing.benchmark.output.folders import ResultFolderFactory

class BenchmarkTest(Protocol):
    test_id: str
    title: str

    def folder_suffix(self) -> str | None:
        ...

    def run(self, runner: "BenchmarkRunner") -> BenchmarkResult:
        ...

    def write_extra_outputs(self, result: BenchmarkResult) -> None:
        ...

class BenchmarkRunner:
    def __init__(self) -> None:
        self.folder_factory = ResultFolderFactory()
        self.files = ResultFileWriter()
        self.console = ConsolePrinter()
        self.client_pool = ClientPool()

    def create_run_folder(
        self,
        config: BenchmarkConfig,
        title: str,
        suffix: str | None,
    ) -> Path:
        folder = self.folder_factory.create(config, suffix=suffix)
        self.files.write_manifest(folder, config, title)
        return folder

    def execute_once(self, config: BenchmarkConfig) -> MetricRow:
        return self.client_pool.execute(config)

    def run_test(self, test: BenchmarkTest) -> BenchmarkResult:
        result = test.run(self)

        self.files.write_graph_values(result.run_folder, result.rows)
        self.files.write_run_summary(result.run_folder, result)
        self.files.write_checks(result.run_folder, result.checks)
        self.files.write_report(result.run_folder, result)

        test.write_extra_outputs(result)

        self.console.print_result(result)
        return result