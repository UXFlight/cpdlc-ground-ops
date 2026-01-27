import mimetypes

from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

from .core import StateStore
from .observability import MetricsStore, register_snapshot_routes
from .transport import Router, register_handlers


def create_app() -> tuple[Flask, SocketIO]:
    mimetypes.add_type("application/javascript", ".js")
    app = Flask(__name__)
    CORS(app)
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

    state_store = StateStore()
    metrics_store = MetricsStore()
    router = Router(socketio, state_store, metrics_store)
    register_handlers(socketio, state_store, metrics_store, router)
    register_snapshot_routes(app, state_store, metrics_store)

    return app, socketio


def main() -> None:
    app, socketio = create_app()
    host = "0.0.0.0"
    port = 5322
    print(f"[TESTING] Server running at http://localhost:{port}")
    socketio.run(app, host=host, port=port, use_reloader=False,
                 allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    main()
