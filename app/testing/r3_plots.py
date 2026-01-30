import json
import os


def _load_r3(results_dir: str) -> list[dict]:
    items = []
    if not os.path.isdir(results_dir):
        return items
    for dirpath, _, filenames in os.walk(results_dir):
        for name in filenames:
            if name != "test_results.json":
                continue
            path = os.path.join(dirpath, name)
            try:
                with open(path, "r", encoding="ascii") as f:
                    data = json.load(f)
                if data.get("test_id") == "R3_capacity":
                    data["_path"] = path
                    items.append(data)
            except Exception:
                continue
    return items


def _extract_points(items: list[dict]) -> list[dict]:
    points = []
    for item in items:
        params = item.get("params", {})
        metrics = item.get("result", {}).get("metrics", {})
        atc = params.get("atc")
        pilots = params.get("pilots")
        end = metrics.get("end_to_end_ms", {})
        server = metrics.get("server_processing_ms", {})
        p50 = end.get("p50")
        p95 = end.get("p95")
        srv_p95 = server.get("p95")
        if atc is None or pilots is None or p50 is None or p95 is None or srv_p95 is None:
            print(f"Skipping incomplete R3 result: {item.get('_path')}")
            continue
        total = int(atc) + int(pilots)
        points.append({
            "total": total,
            "atc": int(atc),
            "pilots": int(pilots),
            "p50": float(p50),
            "p95": float(p95),
            "srv_p95": float(srv_p95),
        })
    return sorted(points, key=lambda p: p["total"])


def _plot_latency(points: list[dict], plot_dir: str) -> None:
    import matplotlib.pyplot as plt
    xs = [p["total"] for p in points]
    p50s = [p["p50"] for p in points]
    p95s = [p["p95"] for p in points]
    plt.figure()
    plt.plot(xs, p50s, color="blue", marker="o", linestyle="-", linewidth=2, markersize=6,
             label="p50 end-to-end latency")
    plt.plot(xs, p95s, color="red", marker="s", linestyle="-", linewidth=2, markersize=6,
             label="p95 end-to-end latency")
    labels = [f"({p['atc']},{p['pilots']})" for p in points]
    for x, y, label in zip(xs, p95s, labels):
        plt.annotate(label, (x, y), textcoords="offset points", xytext=(0, 6),
                     ha="center", fontsize=8)
    plt.xlabel("Total clients (atc, pilots)", fontsize=12)
    plt.ylabel("End-to-end latency (ms)", fontsize=12)
    plt.title("R3 Max Capacity Test End-to-End Latency", fontsize=14)
    plt.grid(True, linestyle="--", linewidth=0.6, alpha=0.5)
    plt.legend(fontsize=11)
    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, "R3_latency_vs_load.png"), dpi=200)

def _plot_server(points: list[dict], plot_dir: str) -> None:
    import matplotlib.pyplot as plt
    xs = [p["total"] for p in points]
    ys = [p["srv_p95"] for p in points]
    plt.figure()
    plt.plot(xs, ys, color="red", marker="s", linestyle="-", linewidth=2, markersize=6,
             label="p95 server processing latency")
    labels = [f"({p['atc']},{p['pilots']})" for p in points]
    for x, y, label in zip(xs, ys, labels):
        plt.annotate(label, (x, y), textcoords="offset points", xytext=(0, 6),
                     ha="center", fontsize=8)
    plt.xlabel("Total clients (atc, pilots)", fontsize=12)
    plt.ylabel("Server processing latency (ms)", fontsize=12)
    plt.title("R3 Max Capacity Test Server Processing Latency", fontsize=14)
    plt.grid(True, linestyle="--", linewidth=0.6, alpha=0.5)
    plt.legend(fontsize=11)
    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, "R3_server_processing_vs_load.png"), dpi=200)


def main() -> None:
    root = os.path.join("app", "testing", "results", "R3")
    plot_dir = os.path.join(root, "plots")
    os.makedirs(plot_dir, exist_ok=True)
    items = _load_r3(root)
    if not items:
        print("No R3_capacity results found. Cannot plot.")
        return
    points = _extract_points(items)
    if not points:
        print("No complete R3_capacity results found. Cannot plot.")
        return
    _plot_latency(points, plot_dir)
    _plot_server(points, plot_dir)


if __name__ == "__main__":
    main()
