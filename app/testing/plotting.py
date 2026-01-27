import os


def _title(test_id: str, atc: int, pilots: int) -> str:
    return f"{test_id} | ATC={atc} | Pilots={pilots}"


def plot_basic(test_id: str, result: dict, params: dict, out_dir: str) -> list[str]:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return []
    metrics = result.get("metrics", {})
    end = metrics.get("end_to_end_ms", {})
    server = metrics.get("server_processing_ms", {})
    atc = params.get("atc") or 0
    pilots = params.get("pilots") or 0
    os.makedirs(out_dir, exist_ok=True)
    outputs: list[str] = []
    # Bars summarize p50/p95 for each run using stored metrics only.
    if end.get("p50") is not None and end.get("p95") is not None:
        plt.figure()
        plt.bar(["p50", "p95"], [end["p50"], end["p95"]])
        plt.ylabel("End-to-end latency (ms)")
        plt.title(_title(test_id, atc, pilots))
        out = os.path.join(out_dir, "latency_p50_p95.png")
        plt.savefig(out, dpi=150, bbox_inches="tight")
        outputs.append(out)
    if server.get("p50") is not None and server.get("p95") is not None:
        plt.figure()
        plt.bar(["p50", "p95"], [server["p50"], server["p95"]])
        plt.ylabel("Server processing time (ms)")
        plt.title(_title(test_id, atc, pilots))
        out = os.path.join(out_dir, "server_processing_p50_p95.png")
        plt.savefig(out, dpi=150, bbox_inches="tight")
        outputs.append(out)
    return outputs


def plot_r3(test_id: str, result: dict, params: dict, out_dir: str) -> list[str]:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return []
    state = result.get("state_summary", {})
    expected_pilots = int(params.get("pilots") or 0)
    expected_atc = int(params.get("atc") or 0)
    pilot_count = int(state.get("pilot_count") or 0)
    atc_count = int(state.get("atc_count") or 0)
    history = state.get("history_lengths", {}) or {}
    min_len = history.get("min", 0)
    avg_len = history.get("avg", 0)
    max_len = history.get("max", 0)
    validation_issues = state.get("validation_issues", []) or []
    polled_issues = result.get("polled_issues", []) or []

    os.makedirs(out_dir, exist_ok=True)
    outputs: list[str] = []
    run_name = os.path.basename(out_dir.rstrip(os.sep))
    plt.figure(figsize=(7, 4.5))

    ax1 = plt.subplot(1, 1, 1)
    labels = ["Pilots", "ATCs"]
    x = [0, 1]
    ax1.bar([i - 0.15 for i in x], [expected_pilots, expected_atc], width=0.3, label="Expected")
    ax1.bar([i + 0.15 for i in x], [pilot_count, atc_count], width=0.3, label="Observed")
    ax1.set_xticks(x, labels)
    ax1.set_ylabel("Client count")
    ax1.set_title("R3 Correctness Test Client Counts")
    ax1.legend()
    issue_text = f"validation_issues={len(validation_issues)}  polled_issues={len(polled_issues)}"
    plt.figtext(0.02, 0.01, issue_text, ha="left", fontsize=9)

    plt.tight_layout(rect=[0, 0.03, 1, 1])
    out = os.path.join(out_dir, f"{run_name}_r3_counts.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    outputs.append(out)

    plt.figure(figsize=(7, 4.5))
    plt.bar(["min", "avg", "max"], [min_len, avg_len, max_len])
    plt.ylabel("Pilot history length")
    plt.title("R3 Correctness Test Pilot History Lengths")
    plt.tight_layout()
    out = os.path.join(out_dir, f"{run_name}_r3_history.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    outputs.append(out)
    return outputs
