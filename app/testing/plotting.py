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


def plot_r2_progress(test_id: str, result: dict, params: dict, out_dir: str) -> list[str]:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return []
    validation = result.get("r3_validation", {}) or {}
    if not validation.get("pass"):
        return []
    progress = validation.get("per_pilot_progress", {}) or {}
    if not progress:
        return []
    os.makedirs(out_dir, exist_ok=True)
    outputs: list[str] = []
    run_name = os.path.basename(out_dir.rstrip(os.sep))
    labels = list(progress.keys())
    values = [progress[k] for k in labels]
    plt.figure(figsize=(7, 4.5))
    plt.bar(labels, values, color="#4c72b0")
    plt.ylabel("Completed interactions per pilot")
    plt.xlabel("Pilots")
    plt.title("R2 Pilot Progress Distribution")
    plt.gca().yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    plt.xticks(rotation=90, fontsize=6)
    plt.tight_layout()
    out = os.path.join(out_dir, f"{run_name}_r2_progress.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    outputs.append(out)
    return outputs
