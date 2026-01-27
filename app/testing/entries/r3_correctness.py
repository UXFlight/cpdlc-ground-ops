import argparse
import json
import os
import time

from ..runners.run_scenarios import run_once


def _format_name(test_id: str, params: dict, stamp: str) -> str:
    dur = int(round(params["duration"]))
    interval = str(params["interval"]).replace(".", "p")
    return f"{test_id}_A{params['atc']:02d}_P{params['pilots']:03d}_D{dur:02d}_I{interval}_{stamp}.txt"


def _write_result(outdir: str, test_id: str, params: dict, result: dict) -> str:
    os.makedirs(outdir, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    name = _format_name(test_id, params, stamp)
    path = os.path.join(outdir, name)
    payload = {"test_id": test_id, "params": params, "result": result}
    with open(path, "w", encoding="ascii") as f:
        f.write(json.dumps(payload, indent=2))
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="http://localhost:5322")
    parser.add_argument("--atc", type=int, required=True)
    parser.add_argument("--pilots", type=int, required=True)
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--pilot-prefix", default="pilot-")
    parser.add_argument("--poll-interval", type=float, default=1.0)
    parser.add_argument("--outdir", default="app/testing/results")
    args = parser.parse_args()

    result = run_once(args.server, args.atc, args.pilots, args.duration,
                      args.interval, args.pilot_prefix, args.poll_interval)
    path = _write_result(args.outdir, "R3_correctness", vars(args), result)
    print(f"[RESULT] {path}")


if __name__ == "__main__":
    main()
