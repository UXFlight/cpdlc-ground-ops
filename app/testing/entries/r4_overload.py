import argparse
import json
import os
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="http://127.0.0.1:5321")
    parser.add_argument("--atc", type=int, required=True)
    parser.add_argument("--pilots", type=int, required=True)
    parser.add_argument("--duration", type=float, default=30.0)
    parser.add_argument("--interval", type=float, default=0.1)
    parser.add_argument("--pilot-prefix", default="pilot-")
    parser.add_argument("--poll-interval", type=float, default=1.0)
    parser.add_argument("--allow-dirty", action="store_true",
                        help="Allow pre-existing pilots/ATCs before starting the test")
    parser.add_argument("--outdir", default="app/testing/results")
    args = parser.parse_args()

    result = run_once(args.server, args.atc, args.pilots, args.duration,
                      args.interval, args.pilot_prefix, args.poll_interval,
                      require_clean_start=not args.allow_dirty)
    path = _write_result(args.outdir, "R4_overload", vars(args), result)
    print(f"[RESULT] {path}")


if __name__ == "__main__":
    main()
