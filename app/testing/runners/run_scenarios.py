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

def run_once(server: str, atc_count: int, pilot_count: int,
             duration: float, interval: float, pilot_prefix: str,
             poll_interval: float) -> dict:
    metrics_start = fetch_json(f"{server}/testing/metrics")
    threads = []
    for i in range(pilot_count):
        client = SystemLoadClient("pilot", server, interval, duration)
        t = threading.Thread(target=client.start, daemon=True)
        threads.append(t)
        t.start()
    time.sleep(1.0)
    for i in range(atc_count):
        client = SystemLoadClient("atc", server, interval, duration)
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
    metrics_delta = {
        "total_messages": metrics_end.get("total_messages", 0) - metrics_start.get("total_messages", 0),
        "total_errors": metrics_end.get("total_errors", 0) - metrics_start.get("total_errors", 0),
        "role_counts": _diff_dict(metrics_start.get("role_counts", {}),
                                  metrics_end.get("role_counts", {})),
        "delivered_counts": _diff_dict(metrics_start.get("delivered_counts", {}),
                                       metrics_end.get("delivered_counts", {})),
    }
    return {
        "metrics": metrics_end,
        "metrics_delta": metrics_delta,
        "state_summary": state,
        "polled_issues": issues,
    }
