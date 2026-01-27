import argparse
import json
import os
import time
from ..runners.run_scenarios import run_once
from ..plotting import plot_r3


def _format_name(test_id: str, params: dict, stamp: str) -> str:
    dur = int(round(params["duration"]))
    interval = str(params["interval"]).replace(".", "p")
    return f"{test_id}_A{params['atc']:02d}_P{params['pilots']:03d}_D{dur:02d}_I{interval}_{stamp}"


def _write_result(outdir: str, test_id: str, params: dict, result: dict) -> str:
    stamp = time.strftime("%H:%M:%S")
    name = _format_name(test_id, params, stamp)
    run_dir = os.path.join(outdir, "R3", name)
    os.makedirs(run_dir, exist_ok=True)
    path = os.path.join(run_dir, "test_results.json")
    payload = {"test_id": test_id, "params": params, "result": result}
    with open(path, "w", encoding="ascii") as f:
        f.write(json.dumps(payload, indent=2))
    plot_r3(test_id, result, params, run_dir)
    return path


def _validate_r3(result: dict, params: dict) -> dict:
    state = result.get("state_summary", {}) or {}
    metrics_delta = result.get("metrics_delta", {}) or {}
    expected_pilots = int(params.get("pilots") or 0)
    expected_atc = int(params.get("atc") or 0)
    pilot_count = int(state.get("pilot_count") or 0)
    atc_count = int(state.get("atc_count") or 0)
    history = state.get("history_lengths", {}) or {}
    min_len = history.get("min", 0)
    max_len = history.get("max", 0)
    total_messages = int(metrics_delta.get("total_messages") or 0)
    validation_issues = state.get("validation_issues", []) or []
    polled_issues = result.get("polled_issues", []) or []

    checks = {
        "pilot_count_matches": pilot_count == expected_pilots,
        "atc_count_matches": atc_count == expected_atc,
        "history_nonzero": min_len > 0,
        "history_bounded": max_len <= max(1, total_messages),
        "validation_issues_empty": len(validation_issues) == 0,
        "polled_issues_empty": len(polled_issues) == 0,
    }
    return {"checks": checks, "pass": all(checks.values())}


def _print_validation(summary: dict) -> None:
    checks = summary.get("checks", {})
    for name in [
        "pilot_count_matches",
        "atc_count_matches",
        "history_nonzero",
        "history_bounded",
        "validation_issues_empty",
        "polled_issues_empty",
    ]:
        status = "PASS" if checks.get(name) else "FAIL"
        print(f"[R3] {name}: {status}")
    result = "PASS" if summary.get("pass") else "FAIL"
    print(f"[R3] Overall: {result}")
    if summary.get("pass"):
        print("[R3] Summary: State remained consistent with no validation issues detected.")
    else:
        print("[R3] Summary: Correctness checks failed; inspect validation_issues and polled_issues.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="http://127.0.0.1:5321")
    parser.add_argument("--atc", type=int, required=True)
    parser.add_argument("--pilots", type=int, required=True)
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--pilot-prefix", default="pilot-")
    parser.add_argument("--poll-interval", type=float, default=1.0)
    parser.add_argument("--connect-timeout", type=float, default=15.0)
    parser.add_argument("--outdir", default="app/testing/results")
    args = parser.parse_args()

    result = run_once(args.server, args.atc, args.pilots, args.duration,
                      args.interval, args.pilot_prefix, args.poll_interval,
                      connect_barrier=True, connect_timeout=args.connect_timeout)
    validation = _validate_r3(result, vars(args))
    result["r3_validation"] = validation
    path = _write_result(args.outdir, "R3_correctness", vars(args), result)
    _print_validation(validation)
    print(f"[RESULT] {path}")


if __name__ == "__main__":
    main()
