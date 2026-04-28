from __future__ import annotations
from pathlib import Path
import matplotlib.pyplot as plt
from app.testing.benchmark.models import MetricRow

IEEE_SINGLE_COLUMN_WIDTH_IN = 3.5
IEEE_DOUBLE_COLUMN_WIDTH_IN = 7.16
FIG_HEIGHT_IN = 2.35
DPI = 300

def _valid(value: float | None) -> bool:
    return value is not None

def _save_current_figure(folder: Path, stem: str) -> None:
    plt.tight_layout()
    plt.savefig(folder / f"{stem}.png", dpi=DPI, bbox_inches="tight")
    plt.savefig(folder / f"{stem}.pdf", bbox_inches="tight")
    plt.close()

def _configure_axes() -> None:
    plt.grid(True, linestyle=":", linewidth=0.6, alpha=0.8)
    plt.tick_params(axis="both", which="major", labelsize=8)
    plt.legend(fontsize=8, frameon=True)


class PlotWriter:
    def write_r1_latency_plot(self, folder: Path, rows: list[MetricRow]) -> None:
        plot_rows = [
            row for row in rows
            if _valid(row.end_to_end_latency.p50_ms)
            and _valid(row.end_to_end_latency.p95_ms)
            and _valid(row.server_processing_latency.p50_ms)
            and _valid(row.server_processing_latency.p95_ms)
        ]

        if not plot_rows:
            return

        x = [row.interval_s for row in plot_rows]

        e2e_p50 = [row.end_to_end_latency.p50_ms for row in plot_rows]
        e2e_p95 = [row.end_to_end_latency.p95_ms for row in plot_rows]
        server_p50 = [row.server_processing_latency.p50_ms for row in plot_rows]
        server_p95 = [row.server_processing_latency.p95_ms for row in plot_rows]

        plt.figure(figsize=(IEEE_SINGLE_COLUMN_WIDTH_IN, FIG_HEIGHT_IN))

        plt.plot(x, e2e_p50, marker="o", color="blue", linestyle="-", linewidth=1.2, markersize=4, label="E2E p50")
        plt.plot(x, e2e_p95, marker="s", color="red", linestyle="-", linewidth=1.2, markersize=4, label="E2E p95")
        plt.plot(x, server_p50, marker="o", color="blue", linestyle="--", linewidth=1.2, markersize=4, label="Server p50")
        plt.plot(x, server_p95, marker="s", color="red", linestyle="--", linewidth=1.2, markersize=4, label="Server p95")

        plt.xlabel("Message interval (s)", fontsize=9)
        plt.ylabel("Latency (ms)", fontsize=9)

        # Lower interval means higher load, so this makes the visual trend easier to read.
        plt.gca().invert_xaxis()

        _configure_axes()
        _save_current_figure(folder, "latency_sensitivity")

    def write_r3_end_to_end_plot(self, folder: Path, rows: list[MetricRow]) -> None:
        plot_rows = [
            row for row in rows
            if row.end_to_end_latency.count > 0
            and _valid(row.end_to_end_latency.p50_ms)
            and _valid(row.end_to_end_latency.p95_ms)
        ]

        if not plot_rows:
            return

        # Use observed total clients because latency can only be interpreted
        # for clients actually admitted/observed during the run.
        x = [row.observed_total for row in plot_rows]
        p50 = [row.end_to_end_latency.p50_ms for row in plot_rows]
        p95 = [row.end_to_end_latency.p95_ms for row in plot_rows]

        plt.figure(figsize=(IEEE_SINGLE_COLUMN_WIDTH_IN, FIG_HEIGHT_IN))

        plt.plot(x, p50, marker="o", color="blue", linestyle="-", linewidth=1.2, markersize=4, label="p50")
        plt.plot(x, p95, marker="s", color="red", linestyle="-", linewidth=1.2, markersize=4, label="p95")

        plt.xlabel("Observed total clients", fontsize=9)
        plt.ylabel("End-to-end latency (ms)", fontsize=9)

        _configure_axes()
        _save_current_figure(folder, "end_to_end_latency")

    def write_r3_server_processing_plot(self, folder: Path, rows: list[MetricRow]) -> None:
        plot_rows = [
            row for row in rows
            if row.server_processing_latency.count > 0
            and _valid(row.server_processing_latency.p50_ms)
            and _valid(row.server_processing_latency.p95_ms)
        ]

        if not plot_rows:
            return

        # Use observed total clients for the same reason as the E2E plot.
        x = [row.observed_total for row in plot_rows]
        p50 = [row.server_processing_latency.p50_ms for row in plot_rows]
        p95 = [row.server_processing_latency.p95_ms for row in plot_rows]

        plt.figure(figsize=(IEEE_SINGLE_COLUMN_WIDTH_IN, FIG_HEIGHT_IN))

        plt.plot(x, p50, marker="o", color="blue", linestyle="-", linewidth=1.2, markersize=4, label="p50")
        plt.plot(x, p95, marker="s", color="red", linestyle="-", linewidth=1.2, markersize=4, label="p95")

        plt.xlabel("Observed total clients", fontsize=9)
        plt.ylabel("Server processing latency (ms)", fontsize=9)

        _configure_axes()
        _save_current_figure(folder, "server_processing_latency")