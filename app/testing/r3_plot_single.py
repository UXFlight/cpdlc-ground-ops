import argparse
import json
import os


def _load(path: str) -> dict:
    with open(path, "r", encoding="ascii") as f:
        return json.load(f)


def _get_history(payload: dict) -> dict | None:
    result = payload.get("result", {}) if isinstance(payload, dict) else {}
    state = result.get("state_summary", {}) if isinstance(result, dict) else {}
    history = state.get("history_lengths", {}) if isinstance(state, dict) else {}
    if not all(k in history for k in ("min", "avg", "max")):
        return None
    return history


def _plot(history: dict, out_path: str) -> bool:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return False
    labels = ["Min history", "Avg history", "Max history"]
    values = [history.get("min", 0), history.get("avg", 0), history.get("max", 0)]
    plt.figure(figsize=(6.5, 4.0))
    plt.bar(labels, values, color="#4c72b0")
    plt.axhline(0, color="#444444", linewidth=1)
    plt.ylabel("History length (completed interactions)")
    plt.title("R3 – Pilot State Consistency")
    plt.gca().yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    plt.tight_layout()
    plt.savefig(out_path, dpi=200, bbox_inches="tight")
    return True


def _find_latest_r3(root: str) -> str | None:
    latest_path = None
    latest_mtime = -1.0
    for base, _, files in os.walk(root):
        for name in files:
            if name != "test_results.json":
                continue
            path = os.path.join(base, name)
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                continue
            if mtime > latest_mtime:
                latest_mtime = mtime
                latest_path = path
    return latest_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot R3 history lengths from test_results.json")
    parser.add_argument("--path", help="Path to R3 test_results.json (optional)")
    parser.add_argument("--root", default="app/testing/results/R3",
                        help="Root folder to search for latest R3 result (default: app/testing/results/R3)")
    args = parser.parse_args()

    target = args.path
    if not target:
        target = _find_latest_r3(args.root)
        if not target:
            print(f"[R3] No test_results.json found under {args.root}")
            return
        print(f"[R3] Using latest result: {target}")

    payload = _load(target)
    history = _get_history(payload)
    if not history:
        print("[R3] Missing history_lengths in test_results.json")
        return
    test_id = payload.get("test_id", "R3_correctness")
    out_dir = os.path.dirname(os.path.abspath(target))
    out_name = f"{test_id}_history_lengths.png"
    out_path = os.path.join(out_dir, out_name)
    if not _plot(history, out_path):
        print("[R3] Plotting failed: matplotlib not available")
        return
    print(f"[R3] Plot saved: {out_path}")


if __name__ == "__main__":
    main()
