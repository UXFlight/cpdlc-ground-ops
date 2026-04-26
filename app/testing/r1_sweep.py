import argparse
import csv
import json
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


def load_r1_rows_from_summary(csv_path: str) -> list[dict]:
    rows = []
    with open(csv_path, "r", encoding="ascii", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            rows.append({
                "interval": float(raw["interval_s"]),
                "result": {
                    "metrics": {
                        "end_to_end_ms": {
                            "p50": float(raw["e2e_p50_ms"]),
                            "p95": float(raw["e2e_p95_ms"]),
                        },
                        "server_processing_ms": {
                            "p50": float(raw["server_p50_ms"]),
                            "p95": float(raw["server_p95_ms"]),
                        },
                        "total_messages": int(raw["total_messages"]),
                        "total_errors": int(raw["total_errors"]),
                    }
                },
                "path": csv_path,
            })
    return rows


def latest_r1_summary_csv(results_root: str) -> str | None:
    if not os.path.isdir(results_root):
        return None
    candidates = [
        os.path.join(results_root, name)
        for name in os.listdir(results_root)
        if name.startswith("R1_summary_") and name.endswith(".csv")
    ]
    if not candidates:
        return None
    return max(candidates, key=os.path.getmtime)


def load_r1_rows(results_root: str) -> list[dict]:
    rows = []
    if not os.path.isdir(results_root):
        return rows
    for dirpath, _, filenames in os.walk(results_root):
        if "test_results.json" not in filenames:
            continue
        path = os.path.join(dirpath, "test_results.json")
        try:
            with open(path, "r", encoding="ascii") as f:
                payload = json.load(f)
        except Exception:
            continue
        if payload.get("test_id") != "R1_latency":
            continue
        params = payload.get("params", {})
        interval = params.get("interval")
        if interval is None:
            continue
        rows.append({
            "interval": interval,
            "params": params,
            "result": payload.get("result", {}),
            "path": path,
        })
    return rows


def plot_r1_sweep(outdir: str, rows: list[dict], output_stem: str = "R1_latency_sweep",
                  use_r1_subdir: bool = True) -> str | None:
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
    root = os.path.join(outdir, "R1") if use_r1_subdir else outdir
    os.makedirs(root, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.0, 4.3))
    ax.plot(xs, e2e_p50, marker="o", markersize=6, linewidth=1.8, label="e2e p50")
    ax.plot(xs, e2e_p95, marker="s", markersize=6, linewidth=1.8, label="e2e p95")
    ax.plot(xs, srv_p50, marker="^", markersize=6, linewidth=1.8, label="server p50")
    ax.plot(xs, srv_p95, marker="D", markersize=6, linewidth=1.8, label="server p95")
    ax.set_xscale("log")
    ax.set_xlabel("Message interval (s)", fontsize=11)
    ax.set_ylabel("Latency (ms)", fontsize=11)
    ax.legend(fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.tick_params(labelsize=10)
    fig.tight_layout()
    out = os.path.join(root, f"{output_stem}.png")
    out_pdf = os.path.join(root, f"{output_stem}.pdf")
    fig.savefig(out, dpi=300, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Regenerate the R1 latency sweep figure from saved results.")
    parser.add_argument("--results-root", default="app/testing/results/R1",
                        help="Directory containing saved R1 test result folders.")
    parser.add_argument("--summary-csv",
                        help="Optional R1 summary CSV to use as the plotting source.")
    parser.add_argument("--outdir", default="images",
                        help="Directory where the regenerated figure will be written.")
    parser.add_argument("--output-stem", default="R1_latency_sweep",
                        help="Output filename stem without extension.")
    args = parser.parse_args()

    summary_csv = args.summary_csv or latest_r1_summary_csv(args.results_root)
    if summary_csv:
        rows = load_r1_rows_from_summary(summary_csv)
    else:
        rows = load_r1_rows(args.results_root)
    out = plot_r1_sweep(args.outdir, rows, args.output_stem, use_r1_subdir=False)
    if not out:
        raise SystemExit("No R1 rows found or matplotlib is unavailable.")
    print(out)


if __name__ == "__main__":
    main()
