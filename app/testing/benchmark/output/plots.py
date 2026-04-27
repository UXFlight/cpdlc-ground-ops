from __future__ import annotations
from pathlib import Path
import matplotlib.pyplot as plt
from app.testing.benchmark.models import MetricRow

class PlotWriter:
    def write_r1_latency_plot(self, folder: Path, rows: list[MetricRow]) -> None:
        x = [row.interval_s for row in rows]

        e2e_p50 = [row.end_to_end_latency.p50_ms for row in rows]
        e2e_p95 = [row.end_to_end_latency.p95_ms for row in rows]
        server_p50 = [row.server_processing_latency.p50_ms for row in rows]
        server_p95 = [row.server_processing_latency.p95_ms for row in rows]

        plt.figure()
        plt.plot(x, e2e_p50, marker="o", color="blue", linestyle="-", label="end-to-end p50")
        plt.plot(x, e2e_p95, marker="o", color="red", linestyle="-", label="end-to-end p95")
        plt.plot(x, server_p50, marker="o", color="blue", linestyle="--", label="server p50")
        plt.plot(x, server_p95, marker="o", color="red", linestyle="--", label="server p95")

        plt.xlabel("Message interval (s)")
        plt.ylabel("Latency (ms)")
        plt.title("R1 latency sensitivity")
        plt.legend()
        plt.grid(True, alpha=0.3)

        plt.savefig(folder / "latency_sensitivity.png", dpi=300, bbox_inches="tight")
        plt.savefig(folder / "latency_sensitivity.pdf", bbox_inches="tight")
        plt.close()

    def write_r3_end_to_end_plot(self, folder: Path, rows: list[MetricRow]) -> None:
        x = [row.requested_total for row in rows]
        p50 = [row.end_to_end_latency.p50_ms for row in rows]
        p95 = [row.end_to_end_latency.p95_ms for row in rows]

        plt.figure()
        plt.plot(x, p50, marker="o", color="blue", label="p50")
        plt.plot(x, p95, marker="o", color="red", label="p95")

        for row in rows:
            plt.annotate(
                f"({row.requested_atc},{row.requested_pilots})",
                (row.requested_total, row.end_to_end_latency.p95_ms or 0),
                textcoords="offset points",
                xytext=(0, 6),
                ha="center",
                fontsize=8,
            )

        plt.xlabel("Requested total clients")
        plt.ylabel("End-to-end latency (ms)")
        plt.title("R3 end-to-end latency")
        plt.legend()
        plt.grid(True, alpha=0.3)

        plt.savefig(folder / "end_to_end_latency.png", dpi=300, bbox_inches="tight")
        plt.savefig(folder / "end_to_end_latency.pdf", bbox_inches="tight")
        plt.close()

    def write_r3_server_processing_plot(self, folder: Path, rows: list[MetricRow]) -> None:
        x = [row.requested_total for row in rows]
        p50 = [row.server_processing_latency.p50_ms for row in rows]
        p95 = [row.server_processing_latency.p95_ms for row in rows]

        plt.figure()
        plt.plot(x, p50, marker="o", color="blue", label="p50")
        plt.plot(x, p95, marker="o", color="red", label="p95")

        for row in rows:
            plt.annotate(
                f"({row.requested_atc},{row.requested_pilots})",
                (row.requested_total, row.server_processing_latency.p95_ms or 0),
                textcoords="offset points",
                xytext=(0, 6),
                ha="center",
                fontsize=8,
            )

        plt.xlabel("Requested total clients")
        plt.ylabel("Server processing latency (ms)")
        plt.title("R3 server-side processing latency")
        plt.legend()
        plt.grid(True, alpha=0.3)

        plt.savefig(folder / "server_processing_latency.png", dpi=300, bbox_inches="tight")
        plt.savefig(folder / "server_processing_latency.pdf", bbox_inches="tight")
        plt.close()
