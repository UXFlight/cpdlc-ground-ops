import json
import threading
import time
import urllib.request

from ..clients.load_client import LoadClient
from ..core.constants import ROLE_ATC, ROLE_PILOT


def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _diff_dict(start: dict, end: dict) -> dict:
    keys = set(start.keys()) | set(end.keys())
    return {k: end.get(k, 0) - start.get(k, 0) for k in keys}

def _summarize_state(state: dict) -> dict:
    pilots = state.get("pilots", {})
    log_lengths = [len(p.get("message_log", [])) for p in pilots.values()]
    avg_len = sum(log_lengths) / len(log_lengths) if log_lengths else 0
    return {
        "pilots_count": len(pilots),
        "atc_pilot_ids_count": len(state.get("atc_state", {}).get("pilot_ids", [])),
        "message_log_lengths": {
            "min": min(log_lengths) if log_lengths else 0,
            "max": max(log_lengths) if log_lengths else 0,
            "avg": avg_len,
        },
        "sample_pilot_ids": list(pilots.keys())[:5],
        "validation_issues": state.get("validation_issues", []),
    }

def run_once(server: str, atc_count: int, pilot_count: int,
             duration: float, interval: float, pilot_prefix: str,
             poll_interval: float) -> dict:
    target_pilots = [f"{pilot_prefix}{i}" for i in range(pilot_count)]
    metrics_start = fetch_json(f"{server}/testing/metrics")
    threads = []
    for i in range(pilot_count):
        client = LoadClient(ROLE_PILOT, f"{pilot_prefix}{i}", server, [],
                            interval, duration)
        t = threading.Thread(target=client.start, daemon=True)
        threads.append(t)
        t.start()
    time.sleep(1.0)
    for i in range(atc_count):
        client = LoadClient(ROLE_ATC, f"atc-{i}", server, target_pilots,
                            interval, duration)
        t = threading.Thread(target=client.start, daemon=True)
        threads.append(t)
        t.start()
    issues = []
    if poll_interval > 0:
        end_ts = time.time() + duration
        while time.time() < end_ts:
            state = fetch_json(f"{server}/testing/state")
            if state.get("validation_issues"):
                issues.extend(state["validation_issues"])
            time.sleep(poll_interval)
    for t in threads:
        t.join()
    metrics_end = fetch_json(f"{server}/testing/metrics")
    state = fetch_json(f"{server}/testing/state")
    state_summary = _summarize_state(state)
    metrics_delta = {
        "total_messages": metrics_end.get("total_messages", 0) - metrics_start.get("total_messages", 0),
        "total_errors": metrics_end.get("total_errors", 0) - metrics_start.get("total_errors", 0),
        "role_counts": _diff_dict(metrics_start.get("role_counts", {}),
                                  metrics_end.get("role_counts", {})),
        "delivered_counts": _diff_dict(metrics_start.get("delivered_counts", {}),
                                       metrics_end.get("delivered_counts", {})),
        "delivered_per_pilot": _diff_dict(metrics_start.get("delivered_per_pilot", {}),
                                          metrics_end.get("delivered_per_pilot", {})),
    }
    return {
        "metrics": metrics_end,
        "metrics_delta": metrics_delta,
        "state_summary": state_summary,
        "polled_issues": issues,
    }
