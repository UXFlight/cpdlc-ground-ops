from __future__ import annotations
import csv
from pathlib import Path
from app.testing.benchmark.models import BenchmarkConfig, BenchmarkResult, CheckResult, MetricRow

def _fmt(value: float | int | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


class ResultFileWriter:
    def write_manifest(self, folder: Path, config: BenchmarkConfig, title: str) -> None:
        path = folder / "run_manifest.txt"

        lines = [
            f"Test: {config.test_id} - {title}",
            f"Server: {config.server_url}",
            f"Requested ATC clients: {config.atc}",
            f"Requested pilot clients: {config.pilots}",
            f"Duration: {config.duration_s:g} s",
            f"Message interval: {config.interval_s:g} s",
        ]

        if config.label:
            lines.append(f"Label: {config.label}")

        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def write_graph_values(self, folder: Path, rows: list[MetricRow]) -> None:
        path = folder / "graph_values.csv"

        fieldnames = [
            "label",
            "requested_atc",
            "requested_pilots",
            "requested_total_clients",
            "observed_atc",
            "observed_pilots",
            "observed_total_clients",
            "duration_s",
            "interval_s",
            "total_messages",
            "total_errors",
            "validation_issues",
            "polling_issues",
            "end_to_end_count",
            "end_to_end_p50_ms",
            "end_to_end_p95_ms",
            "end_to_end_mean_ms",
            "server_processing_count",
            "server_processing_p50_ms",
            "server_processing_p95_ms",
            "server_processing_mean_ms",
        ]

        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for row in rows:
                writer.writerow({
                    "label": row.label,
                    "requested_atc": row.requested_atc,
                    "requested_pilots": row.requested_pilots,
                    "requested_total_clients": row.requested_total,
                    "observed_atc": row.observed_atc,
                    "observed_pilots": row.observed_pilots,
                    "observed_total_clients": row.observed_total,
                    "duration_s": _fmt(row.duration_s),
                    "interval_s": _fmt(row.interval_s),
                    "total_messages": row.total_messages,
                    "total_errors": row.total_errors,
                    "validation_issues": row.validation_issues,
                    "polling_issues": row.polling_issues,
                    "end_to_end_count": row.end_to_end_latency.count,
                    "end_to_end_p50_ms": _fmt(row.end_to_end_latency.p50_ms),
                    "end_to_end_p95_ms": _fmt(row.end_to_end_latency.p95_ms),
                    "end_to_end_mean_ms": _fmt(row.end_to_end_latency.mean_ms),
                    "server_processing_count": row.server_processing_latency.count,
                    "server_processing_p50_ms": _fmt(row.server_processing_latency.p50_ms),
                    "server_processing_p95_ms": _fmt(row.server_processing_latency.p95_ms),
                    "server_processing_mean_ms": _fmt(row.server_processing_latency.mean_ms),
                })

    def write_run_summary(self, folder: Path, result: BenchmarkResult) -> None:
        path = folder / "run_summary.csv"

        fieldnames = [
            "test_id",
            "title",
            "passed",
            "runs",
            "total_messages",
            "total_errors",
            "validation_issues",
            "polling_issues",
        ]

        total_messages = sum(row.total_messages for row in result.rows)
        total_errors = sum(row.total_errors for row in result.rows)
        validation_issues = sum(row.validation_issues for row in result.rows)
        polling_issues = sum(row.polling_issues for row in result.rows)

        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow({
                "test_id": result.test_id,
                "title": result.title,
                "passed": result.passed,
                "runs": len(result.rows),
                "total_messages": total_messages,
                "total_errors": total_errors,
                "validation_issues": validation_issues,
                "polling_issues": polling_issues,
            })

    def write_checks(self, folder: Path, checks: list[CheckResult]) -> None:
        if not checks:
            return

        path = folder / "checks.csv"

        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["check", "passed", "details"])
            writer.writeheader()

            for check in checks:
                writer.writerow({
                    "check": check.name,
                    "passed": check.passed,
                    "details": check.details,
                })

    def write_report(self, folder: Path, result: BenchmarkResult) -> None:
        path = folder / "run_report.txt"

        lines: list[str] = [
            f"{result.test_id} - {result.title}",
            "",
            f"Overall result: {'PASS' if result.passed else 'FAIL'}",
            f"Number of run rows: {len(result.rows)}",
            "",
        ]

        if result.rows:
            lines.append("Run data:")
            for row in result.rows:
                lines.extend([
                    f"  - {row.label}",
                    f"    requested ATC/pilots: {row.requested_atc}/{row.requested_pilots}",
                    f"    observed ATC/pilots: {row.observed_atc}/{row.observed_pilots}",
                    f"    messages: {row.total_messages}",
                    f"    errors: {row.total_errors}",
                    f"    validation issues: {row.validation_issues}",
                    f"    polling issues: {row.polling_issues}",
                    f"    end-to-end p50/p95: {_fmt(row.end_to_end_latency.p50_ms)} / {_fmt(row.end_to_end_latency.p95_ms)} ms",
                    f"    server processing p50/p95: {_fmt(row.server_processing_latency.p50_ms)} / {_fmt(row.server_processing_latency.p95_ms)} ms",
                ])
            lines.append("")

        if result.checks:
            lines.append("Checks:")
            for check in result.checks:
                status = "PASS" if check.passed else "FAIL"
                lines.append(f"  - {check.name}: {status}")
                if check.details:
                    lines.append(f"    {check.details}")
            lines.append("")

        if result.notes:
            lines.append("Notes:")
            for note in result.notes:
                lines.append(f"  - {note}")
            lines.append("")

        path.write_text("\n".join(lines), encoding="utf-8")
