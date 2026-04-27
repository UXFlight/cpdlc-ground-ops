from __future__ import annotations
from datetime import datetime
from pathlib import Path
from app.testing.benchmark.defaults import RESULTS_ROOT, TEST_FOLDER_NAMES
from app.testing.benchmark.models import BenchmarkConfig

def format_seconds(value: float) -> str:
    if value.is_integer():
        return f"{int(value)}s"
    return f"{value:g}s"


def timestamp_for_folder() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

class ResultFolderFactory:
    def __init__(self, root: Path = RESULTS_ROOT):
        self.root = root

    def create(self, config: BenchmarkConfig, suffix: str | None = None) -> Path:
        test_folder = TEST_FOLDER_NAMES[config.test_id]

        parts = [
            timestamp_for_folder(),
            f"{config.atc}_atc",
            f"{config.pilots}_pilots",
            format_seconds(config.duration_s),
            f"{format_seconds(config.interval_s)}_interval",
        ]

        if suffix:
            parts.append(suffix)

        folder_name = "__".join(parts)
        path = self.root / test_folder / folder_name
        path.mkdir(parents=True, exist_ok=False)
        return path
