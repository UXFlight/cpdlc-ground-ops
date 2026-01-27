from flask import Flask, jsonify

from app.managers.pilot_manager import PilotManager
from app.managers.atc_manager import AtcManager
from app.testing.observability.system_metrics import SystemMetrics


def _summarize_state(pilots: list, atcs: list) -> dict:
    history_lengths = [len(p.history) for p in pilots]
    avg_len = sum(history_lengths) / len(history_lengths) if history_lengths else 0
    issues = []
    pilot_ids = {p.sid for p in pilots}
    for p in pilots:
        for update in p.history:
            if update.pilot_sid != p.sid:
                issues.append(f"history_pilot_mismatch:{p.sid}")
                break
    for atc in atcs:
        if atc.selected_pilot and atc.selected_pilot not in pilot_ids:
            issues.append(f"invalid_selected_pilot:{atc.atc_id}")
    return {
        "pilot_count": len(pilots),
        "atc_count": len(atcs),
        "history_lengths": {
            "min": min(history_lengths) if history_lengths else 0,
            "max": max(history_lengths) if history_lengths else 0,
            "avg": avg_len,
        },
        "validation_issues": issues,
    }


def register_system_snapshot(app: Flask, pilot_manager: PilotManager,
                             atc_manager: AtcManager, metrics: SystemMetrics) -> None:
    @app.get("/testing/state")
    def get_state_snapshot():
        pilots = pilot_manager.get_all_pilots()
        atcs = atc_manager.get_all_atcs()
        return jsonify(_summarize_state(pilots, atcs))

    @app.get("/testing/metrics")
    def get_metrics_snapshot():
        return jsonify(metrics.snapshot())
