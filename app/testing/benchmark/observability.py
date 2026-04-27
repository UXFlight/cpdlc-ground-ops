from __future__ import annotations
from typing import Any
from flask import Flask, jsonify


def _history_lengths(pilots: list[Any]) -> dict[str, float | int]:
    lengths = [len(getattr(pilot, "history", [])) for pilot in pilots]

    if not lengths:
        return {
            "min": 0,
            "max": 0,
            "mean": 0.0,
        }

    return {
        "min": min(lengths),
        "max": max(lengths),
        "mean": sum(lengths) / len(lengths),
    }


def _validate_state(pilots: list[Any], atc_list: list[Any]) -> list[str]:
    issues: list[str] = []

    pilot_sids = [getattr(pilot, "sid", None) for pilot in pilots]
    if len(pilot_sids) != len(set(pilot_sids)):
        issues.append("duplicate_pilot_sid")

    atc_sids = []
    for atc in atc_list:
        if isinstance(atc, dict):
            atc_sids.append(atc.get("sid"))
        else:
            atc_sids.append(getattr(atc, "atc_id", None))

    if len(atc_sids) != len(set(atc_sids)):
        issues.append("duplicate_atc_sid")

    for pilot in pilots:
        sid = getattr(pilot, "sid", "unknown")

        steps = getattr(pilot, "steps", {})
        if not isinstance(steps, dict):
            issues.append(f"pilot_{sid}_steps_not_dict")
            continue

        for step_code, step in steps.items():
            request_id = getattr(step, "request_id", None)
            status = getattr(step, "status", None)

            if not request_id:
                issues.append(f"pilot_{sid}_step_{step_code}_missing_request_id")

            if status is None:
                issues.append(f"pilot_{sid}_step_{step_code}_missing_status")

    return issues


def register_benchmark_observability(
    app: Flask,
    pilot_manager,
    atc_manager,
    metrics_store,
) -> None:
    @app.post("/testing/benchmark/reset")
    def benchmark_reset():
        metrics_store.reset()
        return jsonify({"ok": True})

    @app.get("/testing/benchmark/metrics")
    def benchmark_metrics():
        return jsonify(metrics_store.snapshot())

    @app.get("/testing/benchmark/state")
    def benchmark_state():
        pilots = pilot_manager.get_all_pilots()
        atc_list = atc_manager.get_all()

        validation_issues = _validate_state(pilots, atc_list)

        return jsonify({
            "pilot_count": len(pilots),
            "atc_count": len(atc_list),
            "history_lengths": _history_lengths(pilots),
            "validation_issues": validation_issues,
        })