import argparse
import json
import os
import time
from ..runners.run_scenarios import run_once
from ..plotting import plot_basic
from ..r2_sweep import write_r2_summary, plot_r2_sweep

SWEEP_INTERVALS = [2.0, 1.0, 0.5, 0.25, 0.1]
SWEEP_ATC = 5
SWEEP_PILOTS = 20
SWEEP_DURATION = 60.0


def _format_name(test_id: str, params: dict, stamp: str) -> str:
    dur = int(round(params["duration"]))
    interval = str(params["interval"]).replace(".", "p")
    return f"{test_id}_A{params['atc']:02d}_P{params['pilots']:03d}_D{dur:02d}_I{interval}_{stamp}"


def _write_result(outdir: str, test_id: str, params: dict, result: dict) -> str:
    stamp = time.strftime("%H:%M:%S")
    name = _format_name(test_id, params, stamp)
    run_dir = os.path.join(outdir, "R2", name)
    os.makedirs(run_dir, exist_ok=True)
    path = os.path.join(run_dir, "test_results.json")
    payload = {"test_id": test_id, "params": params, "result": result}
    with open(path, "w", encoding="ascii") as f:
        f.write(json.dumps(payload, indent=2))
    plot_basic(test_id, result, params, run_dir)
    return path


def _log_context(server: str) -> None:
    print("[R2] No test server started. Using existing server only.")
    print(f"[R2] Target server: {server}")
    print("[R2] Events exercised: sendRequest, new_request, atcResponse, sendAction, getPilotList")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="http://127.0.0.1:5321")
    parser.add_argument("--atc", type=int, required=True)
    parser.add_argument("--pilots", type=int, required=True)
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--pilot-prefix", default="pilot-")
    parser.add_argument("--poll-interval", type=float, default=0.0)
    parser.add_argument("--outdir", default="app/testing/results")
    parser.add_argument("--sweep", action="store_true", help="Run R2 sweep over fixed intervals")
    args = parser.parse_args()

    _log_context(args.server)
    if not args.sweep:
        result = run_once(args.server, args.atc, args.pilots, args.duration,
                          args.interval, args.pilot_prefix, args.poll_interval)
        path = _write_result(args.outdir, "R2_latency", vars(args), result)
        print(f"[RESULT] {path}")
        return
    if (args.atc, args.pilots, args.duration) != (SWEEP_ATC, SWEEP_PILOTS, SWEEP_DURATION):
        print(f"[R2] Sweep forces ATC={SWEEP_ATC} Pilots={SWEEP_PILOTS} Duration={int(SWEEP_DURATION)}s")
    rows = []
    for interval in SWEEP_INTERVALS:
        print(f"[R2] Running interval={interval}s")
        params = vars(args) | {"atc": SWEEP_ATC, "pilots": SWEEP_PILOTS,
                               "duration": SWEEP_DURATION, "interval": interval}
        result = run_once(args.server, SWEEP_ATC, SWEEP_PILOTS, SWEEP_DURATION,
                          interval, args.pilot_prefix, args.poll_interval)
        path = _write_result(args.outdir, "R2_latency", params, result)
        rows.append({"interval": interval, "params": params, "result": result, "path": path})
        metrics = result.get("metrics", {})
        end = metrics.get("end_to_end_ms", {})
        server = metrics.get("server_processing_ms", {})
        print(f"[R2] interval={interval}s e2e_p50={end.get('p50')} e2e_p95={end.get('p95')}"
              f" server_p50={server.get('p50')} server_p95={server.get('p95')}"
              f" msgs={metrics.get('total_messages')} errs={metrics.get('total_errors')}")
    summary_path = write_r2_summary(args.outdir, rows)
    plot_path = plot_r2_sweep(args.outdir, rows)
    print(f"[R2] Summary: {summary_path}")
    if plot_path:
        print(f"[R2] Plot: {plot_path}")


if __name__ == "__main__":
    main()
