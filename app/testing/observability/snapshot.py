from flask import Flask, jsonify

from .metrics import MetricsStore
from ..core.state import StateStore


def register_snapshot_routes(app: Flask, state_store: StateStore,
                             metrics_store: MetricsStore) -> None:
    @app.get("/testing/state")
    def get_state_snapshot():
        payload = state_store.snapshot()
        payload["validation_issues"] = state_store.validate_state()
        return jsonify(payload)

    @app.get("/testing/metrics")
    def get_metrics_snapshot():
        return jsonify(metrics_store.snapshot())
