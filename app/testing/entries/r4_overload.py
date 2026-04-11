import argparse
import json
import os
import threading
import time
from ..runners.run_scenarios import run_once
from ..plotting import plot_basic


def _format_name(test_id: str, params: dict, stamp: str) -> str:
    dur = int(round(params["duration"]))
    interval = str(params["interval"]).replace(".", "p")
    return f"{test_id}_A{params['atc']:02d}_P{params['pilots']:03d}_D{dur:02d}_I{interval}_{stamp}"


def _write_result(outdir: str, test_id: str, params: dict, result: dict) -> str:
    stamp = time.strftime("%H:%M:%S")
    name = _format_name(test_id, params, stamp)
    run_dir = os.path.join(outdir, "R4", name)
    os.makedirs(run_dir, exist_ok=True)
    path = os.path.join(run_dir, "test_results.json")
    payload = {"test_id": test_id, "params": params, "result": result}
    with open(path, "w", encoding="ascii") as f:
        f.write(json.dumps(payload, indent=2))
    plot_basic(test_id, result, params, run_dir)
    return path


def _analyze_overload(result: dict, params: dict) -> dict:
    expected_pilots = int(params.get("pilots") or 0)
    expected_atc = int(params.get("atc") or 0)
    metrics_delta = result.get("metrics_delta", {}) or {}
    state = result.get("state_summary", {}) or {}
    validation_issues = state.get("validation_issues", []) or []
    polled_issues = result.get("polled_issues", []) or []

    observed_pilots = int(state.get("pilot_count") or 0)
    observed_atc = int(state.get("atc_count") or 0)
    total_errors = int(metrics_delta.get("total_errors", 0) or 0)
    total_messages = int(metrics_delta.get("total_messages", 0) or 0)
    error_rate = (total_errors / total_messages) if total_messages > 0 else 0.0

    return {
        "expected_counts": {"pilots": expected_pilots, "atc": expected_atc},
        "observed_counts": {"pilots": observed_pilots, "atc": observed_atc},
        "total_errors": total_errors,
        "total_messages": total_messages,
        "error_rate": error_rate,
        "validation_issues": list(validation_issues),
        "polled_issues": list(polled_issues),
    }


def _start_sys_monitor(enabled: bool, interval_s: float) -> tuple[threading.Event, list[dict]]:
    stop_event = threading.Event()
    samples: list[dict] = []
    if not enabled:
        return stop_event, samples
    try:
        import psutil  # type: ignore
    except Exception:
        print("[R4] psutil not available; skipping CPU/RAM monitoring.")
        return stop_event, samples

    def run():
        while not stop_event.is_set():
            samples.append({
                "ts": time.time(),
                "cpu_percent": psutil.cpu_percent(interval=None),
                "ram_percent": psutil.virtual_memory().percent,
            })
            time.sleep(max(interval_s, 0.1))

    t = threading.Thread(target=run, daemon=True)
    t.start()
    return stop_event, samples


def _summarize_sys(samples: list[dict]) -> dict | None:
    if not samples:
        return None
    cpu = [s["cpu_percent"] for s in samples]
    ram = [s["ram_percent"] for s in samples]
    return {
        "samples": len(samples),
        "cpu_percent": {"avg": sum(cpu) / len(cpu), "max": max(cpu)},
        "ram_percent": {"avg": sum(ram) / len(ram), "max": max(ram)},
    }


def _print_summary(summary: dict) -> None:
    expected = summary.get("expected_counts", {})
    observed = summary.get("observed_counts", {})
    print(f"[R4] expected pilots/atc: {expected.get('pilots', 0)}/{expected.get('atc', 0)}")
    print(f"[R4] observed pilots/atc: {observed.get('pilots', 0)}/{observed.get('atc', 0)}")
    print(f"[R4] total_errors: {summary.get('total_errors', 0)}")
    print(f"[R4] total_messages: {summary.get('total_messages', 0)}")
    print(f"[R4] error_rate: {summary.get('error_rate', 0.0):.4f}")
    if summary.get("validation_issues"):
        print(f"[R4] validation_issues: {len(summary.get('validation_issues', []))}")
    if summary.get("polled_issues"):
        print(f"[R4] polled_issues: {len(summary.get('polled_issues', []))}")
    sys_usage = summary.get("system_usage")
    if sys_usage:
        cpu = sys_usage.get("cpu_percent", {})
        ram = sys_usage.get("ram_percent", {})
        print(f"[R4] cpu_percent avg/max: {cpu.get('avg', 0):.1f}/{cpu.get('max', 0):.1f}")
        print(f"[R4] ram_percent avg/max: {ram.get('avg', 0):.1f}/{ram.get('max', 0):.1f}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="http://127.0.0.1:5321")
    parser.add_argument("--atc", type=int, required=True)
    parser.add_argument("--pilots", type=int, required=True)
    parser.add_argument("--duration", type=float, default=30.0)
    parser.add_argument("--interval", type=float, default=0.1)
    parser.add_argument("--pilot-prefix", default="pilot-")
    parser.add_argument("--poll-interval", type=float, default=1.0)
    parser.add_argument("--http-timeout", type=float, default=5.0)
    parser.add_argument("--http-retries", type=int, default=0)
    parser.add_argument("--monitor-sys", action="store_true", default=True,
                        help="Record CPU/RAM usage during the test (requires psutil).")
    parser.add_argument("--no-monitor-sys", action="store_false", dest="monitor_sys",
                        help="Disable CPU/RAM monitoring.")
    parser.add_argument("--monitor-interval", type=float, default=1.0,
                        help="CPU/RAM sample interval in seconds.")
    parser.add_argument("--allow-dirty", action="store_true",
                        help="Allow pre-existing pilots/ATCs before starting the test")
    parser.add_argument("--outdir", default="app/testing/results")
    args = parser.parse_args()

    stop_event, samples = _start_sys_monitor(args.monitor_sys, args.monitor_interval)
    result = run_once(args.server, args.atc, args.pilots, args.duration,
                      args.interval, args.pilot_prefix, args.poll_interval,
                      require_clean_start=not args.allow_dirty,
                      http_timeout=args.http_timeout, http_retries=args.http_retries)
    stop_event.set()
    summary = _analyze_overload(result, vars(args))
    summary["system_usage"] = _summarize_sys(samples)
    result["r4_overload"] = summary
    path = _write_result(args.outdir, "R4_overload", vars(args), result)
    _print_summary(summary)
    print(f"[RESULT] {path}")


if __name__ == "__main__":
    main()
