import json
import threading
import time
import urllib.request

from ..clients.system_load_client import SystemLoadClient


def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _diff_dict(start: dict, end: dict) -> dict:
    keys = set(start.keys()) | set(end.keys())
    return {k: end.get(k, 0) - start.get(k, 0) for k in keys}

def _pick_better_state(best: dict | None, candidate: dict) -> dict:
    if not best:
        return candidate
    best_pilots = int(best.get("pilot_count") or 0)
    best_atc = int(best.get("atc_count") or 0)
    cand_pilots = int(candidate.get("pilot_count") or 0)
    cand_atc = int(candidate.get("atc_count") or 0)
    if (cand_pilots + cand_atc) >= (best_pilots + best_atc):
        return candidate
    return best

def _pick_better_history(best: dict | None, candidate: dict) -> dict:
    if not best:
        return candidate
    best_hist = best.get("history_lengths", {}) or {}
    cand_hist = candidate.get("history_lengths", {}) or {}
    if (cand_hist.get("max", 0) or 0) >= (best_hist.get("max", 0) or 0):
        return candidate
    return best

def _merge_state(best_counts: dict | None, best_history: dict | None, last: dict | None) -> dict:
    base = last or {}
    out = dict(base)
    if best_counts:
        out["pilot_count"] = best_counts.get("pilot_count", out.get("pilot_count", 0))
        out["atc_count"] = best_counts.get("atc_count", out.get("atc_count", 0))
    if best_history:
        out["history_lengths"] = best_history.get("history_lengths", out.get("history_lengths", {}))
        out["validation_issues"] = best_history.get("validation_issues", out.get("validation_issues", []))
    return out

def run_once(server: str, atc_count: int, pilot_count: int,
             duration: float, interval: float, pilot_prefix: str,
             poll_interval: float, connect_barrier: bool = False,
             connect_timeout: float = 10.0, record_snapshots: bool = False) -> dict:
    metrics_start = fetch_json(f"{server}/testing/metrics")
    threads = []
    pilot_clients = []
    start_event = threading.Event() if connect_barrier else None
    for i in range(pilot_count):
        client = SystemLoadClient("pilot", server, interval, duration, start_event=start_event,
                                  client_id=f"{pilot_prefix}{i}")
        pilot_clients.append(client)
        t = threading.Thread(target=client.start, daemon=True)
        threads.append(t)
        t.start()
    time.sleep(1.0)
    for i in range(atc_count):
        client = SystemLoadClient("atc", server, interval, duration, i, atc_count, start_event=start_event)
        t = threading.Thread(target=client.start, daemon=True)
        threads.append(t)
        t.start()
    issues = []
    last_state = None
    best_state = None
    best_history_state = None
    snapshots = []
    initial_state = fetch_json(f"{server}/testing/state")
    last_state = initial_state
    best_state = _pick_better_state(best_state, initial_state)
    best_history_state = _pick_better_history(best_history_state, initial_state)
    if record_snapshots:
        snapshots.append(initial_state)
    if connect_barrier and start_event:
        deadline = time.time() + max(connect_timeout, 0.0)
        while time.time() < deadline:
            state = fetch_json(f"{server}/testing/state")
            last_state = state
            best_state = _pick_better_state(best_state, state)
            best_history_state = _pick_better_history(best_history_state, state)
            if record_snapshots:
                snapshots.append(state)
            if state.get("pilot_count") == pilot_count and state.get("atc_count") == atc_count:
                break
            time.sleep(0.2)
        if (last_state or {}).get("pilot_count") != pilot_count:
            issues.append(f"connect_shortfall_pilots:{(last_state or {}).get('pilot_count', 0)}/{pilot_count}")
        if (last_state or {}).get("atc_count") != atc_count:
            issues.append(f"connect_shortfall_atc:{(last_state or {}).get('atc_count', 0)}/{atc_count}")
        start_event.set()
    if poll_interval > 0:
        end_ts = time.time() + duration
        while time.time() < end_ts:
            state = fetch_json(f"{server}/testing/state")
            last_state = state
            best_state = _pick_better_state(best_state, state)
            best_history_state = _pick_better_history(best_history_state, state)
            if record_snapshots:
                snapshots.append(state)
            if state.get("validation_issues"):
                issues.extend(state["validation_issues"])
            time.sleep(poll_interval)
    for t in threads:
        t.join()
    metrics_end = fetch_json(f"{server}/testing/metrics")
    state = _merge_state(best_state, best_history_state, last_state or fetch_json(f"{server}/testing/state"))
    metrics_delta = {
        "total_messages": metrics_end.get("total_messages", 0) - metrics_start.get("total_messages", 0),
        "total_errors": metrics_end.get("total_errors", 0) - metrics_start.get("total_errors", 0),
        "role_counts": _diff_dict(metrics_start.get("role_counts", {}),
                                  metrics_end.get("role_counts", {})),
        "delivered_counts": _diff_dict(metrics_start.get("delivered_counts", {}),
                                       metrics_end.get("delivered_counts", {})),
    }
    result = {
        "metrics": metrics_end,
        "metrics_delta": metrics_delta,
        "state_summary": state,
        "polled_issues": issues,
    }
    if record_snapshots:
        result["snapshots"] = snapshots
        result["client_stats"] = {"pilots": [c.stats() for c in pilot_clients]}
    return result
