import csv
import os
import time


def write_r1_summary(outdir: str, rows: list[dict]) -> str:
    stamp = time.strftime("%H:%M:%S")
    root = os.path.join(outdir, "R1")
    os.makedirs(root, exist_ok=True)
    json_path = os.path.join(root, f"R1_summary_{stamp}.json")
    with open(json_path, "w", encoding="ascii") as f:
        f.write(__import__("json").dumps(rows, indent=2))
    csv_path = os.path.join(root, f"R1_summary_{stamp}.csv")
    with open(csv_path, "w", encoding="ascii", newline="") as f:
        w = csv.writer(f)
        w.writerow(["interval_s", "e2e_p50_ms", "e2e_p95_ms", "server_p50_ms",
                    "server_p95_ms", "total_messages", "total_errors"])
        for row in rows:
            metrics = row.get("result", {}).get("metrics", {})
            end = metrics.get("end_to_end_ms", {})
            server = metrics.get("server_processing_ms", {})
            w.writerow([
                row.get("interval"),
                end.get("p50"),
                end.get("p95"),
                server.get("p50"),
                server.get("p95"),
                metrics.get("total_messages"),
                metrics.get("total_errors"),
            ])
    return json_path


def plot_r1_sweep(outdir: str, rows: list[dict]) -> str | None:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return None
    if not rows:
        return None
    rows_sorted = sorted(rows, key=lambda r: r.get("interval", 0))
    xs = [r.get("interval") for r in rows_sorted]
    e2e_p50 = [r.get("result", {}).get("metrics", {}).get("end_to_end_ms", {}).get("p50") for r in rows_sorted]
    e2e_p95 = [r.get("result", {}).get("metrics", {}).get("end_to_end_ms", {}).get("p95") for r in rows_sorted]
    srv_p50 = [r.get("result", {}).get("metrics", {}).get("server_processing_ms", {}).get("p50") for r in rows_sorted]
    srv_p95 = [r.get("result", {}).get("metrics", {}).get("server_processing_ms", {}).get("p95") for r in rows_sorted]
    root = os.path.join(outdir, "R1")
    os.makedirs(root, exist_ok=True)
    plt.figure(figsize=(7, 4.5))
    plt.plot(xs, e2e_p50, marker="o", label="e2e p50")
    plt.plot(xs, e2e_p95, marker="s", label="e2e p95")
    plt.plot(xs, srv_p50, marker="^", label="server p50")
    plt.plot(xs, srv_p95, marker="D", label="server p95")
    plt.xscale("log")
    plt.xlabel("Message interval (s)")
    plt.ylabel("Latency (ms)")
    plt.title("R1 Latency Sensitivity Test")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.4)
    out = os.path.join(root, "R1_latency_sweep.png")
    plt.tight_layout()
    plt.savefig(out, dpi=200, bbox_inches="tight")
    return out
