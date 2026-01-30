import argparse
import json
import os
import time
from ..runners.run_scenarios import run_once
from ..plotting import plot_r2_progress


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
    plot_r2_progress(test_id, result, params, run_dir)
    return path


def _validate_r2(result: dict, params: dict) -> dict:
    expected_pilots = int(params.get("pilots") or 0)
    expected_atc = int(params.get("atc") or 0)
    min_cycles = int(params.get("min_cycles") or 3)
    snapshots = result.get("snapshots", []) or []
    state = result.get("state_summary", {}) or {}
    validation_issues = state.get("validation_issues", []) or []
    polled_issues = result.get("polled_issues", []) or []
    pilot_stats = result.get("client_stats", {}).get("pilots", []) or []

    reasons = []
    checks = {}

    steady_index = None
    for i, snap in enumerate(snapshots):
        if snap.get("pilot_count") == expected_pilots and snap.get("atc_count") == expected_atc:
            steady_index = i
            break
    if steady_index is None:
        checks["population_integrity"] = False
        reasons.append("steady_state_not_reached")
    else:
        checks["population_integrity"] = True

    unexpected = {}
    for p in pilot_stats:
        if p.get("unexpected_events"):
            unexpected[p.get("client_id", "pilot")] = p.get("unexpected_events")
    checks["per_pilot_isolation"] = len(unexpected) == 0
    if unexpected:
        reasons.append("unexpected_events_detected")

    progress_fail = []
    for p in pilot_stats:
        if (p.get("completed_cycles") or 0) < min_cycles:
            progress_fail.append(p.get("client_id", "pilot"))
    checks["progress_guarantee"] = len(progress_fail) == 0
    if progress_fail:
        reasons.append("insufficient_completed_cycles")

    if steady_index is None:
        history_series = [s.get("history_lengths", {}) for s in snapshots]
    else:
        history_series = [s.get("history_lengths", {}) for s in snapshots[steady_index:]]
    max_series = [h.get("max", 0) for h in history_series if h]
    monotonic = all(b >= a for a, b in zip(max_series, max_series[1:])) if max_series else False
    max_completed = max([p.get("completed_cycles", 0) for p in pilot_stats] or [0])
    expected_bound = max_completed * 3 + 1
    bounded = True
    if max_series:
        bounded = max(max_series) <= expected_bound
    checks["bounded_state_growth"] = monotonic and bounded
    if not monotonic:
        reasons.append("history_not_monotonic")
    if not bounded:
        reasons.append("history_exceeds_expected_bound")

    checks["validation_issues_empty"] = len(validation_issues) == 0
    if validation_issues:
        reasons.append("validation_issues_present")
    checks["polled_issues_empty"] = len(polled_issues) == 0
    if polled_issues:
        reasons.append("polled_issues_present")

    per_pilot_progress = {p.get("client_id", "pilot"): p.get("completed_cycles", 0) for p in pilot_stats}
    return {
        "checks": checks,
        "pass": all(checks.values()),
        "reasons": reasons,
        "per_pilot_progress": per_pilot_progress,
        "unexpected_events": unexpected,
        "min_cycles_required": min_cycles,
    }


def _print_validation(summary: dict, params: dict, result: dict) -> None:
    checks = summary.get("checks", {})
    expected_pilots = int(params.get("pilots") or 0)
    expected_atc = int(params.get("atc") or 0)
    state = result.get("state_summary", {}) or {}
    observed_pilots = int(state.get("pilot_count") or 0)
    observed_atc = int(state.get("atc_count") or 0)
    progress = summary.get("per_pilot_progress", {}) or {}
    min_cycles = summary.get("min_cycles_required", 0)
    metrics_delta = result.get("metrics_delta", {}) or {}
    validation_issues = state.get("validation_issues", []) or []
    polled_issues = result.get("polled_issues", []) or []
    unexpected = summary.get("unexpected_events", {}) or {}
    if progress:
        min_done = min(progress.values())
        max_done = max(progress.values())
    else:
        min_done = 0
        max_done = 0
    below_min = [k for k, v in progress.items() if v < min_cycles]
    for name in [
        "population_integrity",
        "per_pilot_isolation",
        "progress_guarantee",
        "bounded_state_growth",
        "validation_issues_empty",
        "polled_issues_empty",
    ]:
        status = "PASS" if checks.get(name) else "FAIL"
        print(f"[R2] {name}: {status}")
    print(f"[R2] expected pilots/atc: {expected_pilots}/{expected_atc}")
    print(f"[R2] observed pilots/atc: {observed_pilots}/{observed_atc}")
    print(f"[R2] cycles min/req/max: {min_done}/{min_cycles}/{max_done}")
    print(f"[R2] pilots below min_cycles: {len(below_min)}")
    print(f"[R2] validation_issues: {len(validation_issues)}")
    print(f"[R2] polled_issues: {len(polled_issues)}")
    print(f"[R2] unexpected_events: {sum(len(v) for v in unexpected.values())}")
    print(f"[R2] total_errors (delta): {metrics_delta.get('total_errors', 0)}")
    print(f"[R2] total_messages (delta): {metrics_delta.get('total_messages', 0)}")
    result = "PASS" if summary.get("pass") else "FAIL"
    print(f"[R2] Overall: {result}")
    if summary.get("pass"):
        print("[R2] Summary: State remained consistent; pilots progressed and no isolation issues were detected.")
    else:
        reasons = ", ".join(summary.get("reasons", [])) or "unspecified"
        print(f"[R2] Summary: Correctness checks failed ({reasons}).")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="http://127.0.0.1:5321")
    parser.add_argument("--atc", type=int, required=True)
    parser.add_argument("--pilots", type=int, required=True)
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--pilot-prefix", default="pilot-")
    parser.add_argument("--poll-interval", type=float, default=1.0)
    parser.add_argument("--min-cycles", type=int, default=3)
    parser.add_argument("--connect-timeout", type=float, default=15.0)
    parser.add_argument("--teardown-grace", type=float, default=2.0,
                        help="Stop polling before teardown to avoid disconnect snapshots")
    parser.add_argument("--allow-dirty", action="store_true",
                        help="Allow pre-existing pilots/ATCs before starting the test")
    parser.add_argument("--outdir", default="app/testing/results")
    args = parser.parse_args()

    result = run_once(args.server, args.atc, args.pilots, args.duration,
                      args.interval, args.pilot_prefix, args.poll_interval,
                      connect_barrier=True, connect_timeout=args.connect_timeout,
                      record_snapshots=True, poll_end_offset=args.teardown_grace,
                      require_clean_start=not args.allow_dirty)
    validation = _validate_r2(result, vars(args))
    result["r3_validation"] = validation
    path = _write_result(args.outdir, "R2_correctness", vars(args), result)
    _print_validation(validation, vars(args), result)
    print(f"[RESULT] {path}")


if __name__ == "__main__":
    main()
