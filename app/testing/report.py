import argparse
import json
import os


ARCH_TEXT = """System Architecture
The testing subsystem implements a client-server, real-time CPDLC ground
communication model. Pilot clients maintain isolated per-pilot state, while
ATC clients share a single logical state view synchronized across controllers.
The server coordinates registration, routing, and state updates, exposing a
read-only snapshot interface for validation and metrics collection.

Validated Real-Time and Stress Test Results
"""


def _load_results(results_dir: str) -> list:
    items = []
    if not os.path.isdir(results_dir):
        return items
    for name in sorted(os.listdir(results_dir)):
        if not name.endswith(".txt"):
            continue
        path = os.path.join(results_dir, name)
        try:
            with open(path, "r", encoding="ascii") as f:
                items.append(json.load(f))
        except Exception:
            continue
    return items


def _summarize_results(items: list) -> str:
    if not items:
        return "This could not be validated from the available artifacts.\n"
    lines = []
    for item in items:
        params = item.get("params", {})
        metrics = item.get("result", {}).get("metrics_delta", {})
        p50 = item.get("result", {}).get("metrics", {}).get("end_to_end_ms", {}).get("p50")
        p95 = item.get("result", {}).get("metrics", {}).get("end_to_end_ms", {}).get("p95")
        lines.append(
            f"- run: atc={params.get('atc')}, pilots={params.get('pilots')}, "
            f"duration={params.get('duration')}s, interval={params.get('interval')}s, "
            f"msgs={metrics.get('total_messages')}, p50_ms={p50}, p95_ms={p95}"
        )
    return "\n".join(lines) + "\n"


def _plot_if_requested(items: list, results_dir: str) -> str:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return "Optional Plots Summary\nThis could not be validated from the available artifacts.\n"
    if not items:
        return "Optional Plots Summary\nThis could not be validated from the available artifacts.\n"
    plot_dir = os.path.join(results_dir, "plots")
    os.makedirs(plot_dir, exist_ok=True)
    xs, p50s, p95s = [], [], []
    for item in items:
        params = item.get("params", {})
        total = (params.get("atc") or 0) + (params.get("pilots") or 0)
        lat = item.get("result", {}).get("metrics", {}).get("end_to_end_ms", {})
        xs.append(total)
        p50s.append(lat.get("p50"))
        p95s.append(lat.get("p95"))
    plt.figure()
    plt.plot(xs, p50s, "o-", label="p50")
    plt.plot(xs, p95s, "o-", label="p95")
    plt.xlabel("Total clients (ATC + pilots)")
    plt.ylabel("End-to-end latency (ms)")
    plt.legend()
    out = os.path.join(plot_dir, "latency_vs_clients.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    return f"Optional Plots Summary\n- {out}\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", default="app/testing/results")
    parser.add_argument("--p", action="store_true", help="generate plots")
    args = parser.parse_args()
    items = _load_results(args.results_dir)
    text = ARCH_TEXT + _summarize_results(items)
    if args.p:
        text += "\n" + _plot_if_requested(items, args.results_dir)
    print(text, end="")


if __name__ == "__main__":
    main()
