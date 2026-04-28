from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

TestId = Literal["R1", "R2", "R3", "R4"]


@dataclass(frozen=True)
class BenchmarkConfig:
    test_id: TestId
    server_url: str
    atc: int
    pilots: int
    duration_s: float
    interval_s: float
    label: str = ""


@dataclass(frozen=True)
class LatencyStats:
    count: int = 0
    p50_ms: float | None = None
    p95_ms: float | None = None
    mean_ms: float | None = None
    min_ms: float | None = None
    max_ms: float | None = None


@dataclass
class MetricRow:
    label: str
    test_id: TestId

    requested_atc: int
    requested_pilots: int
    observed_atc: int
    observed_pilots: int

    duration_s: float
    interval_s: float

    total_messages: int
    total_errors: int
    validation_issues: int
    polling_issues: int

    end_to_end_latency: LatencyStats
    server_processing_latency: LatencyStats

    details: dict[str, Any] = field(default_factory=dict)

    @property
    def requested_total(self) -> int:
        return self.requested_atc + self.requested_pilots

    @property
    def observed_total(self) -> int:
        return self.observed_atc + self.observed_pilots

    @property
    def dropped_atc(self) -> int:
        return max(self.requested_atc - self.observed_atc, 0)

    @property
    def dropped_pilots(self) -> int:
        return max(self.requested_pilots - self.observed_pilots, 0)

    @property
    def dropped_total(self) -> int:
        return self.dropped_atc + self.dropped_pilots


@dataclass
class CheckResult:
    name: str
    passed: bool
    details: str = ""


@dataclass
class BenchmarkResult:
    test_id: TestId
    title: str
    run_folder: Path
    rows: list[MetricRow] = field(default_factory=list)
    checks: list[CheckResult] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks) if self.checks else True