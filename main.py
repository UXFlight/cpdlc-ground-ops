try:
    import eventlet
    eventlet.monkey_patch()
except Exception:
    eventlet = None

import argparse
import logging
import mimetypes
import os
import signal
import sys
import threading
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from app.classes.socket import SocketService
from app.managers import PilotManager, SocketManager, AtcManager, AirportMapManager
from app.routes import general
from app.testing.benchmark.metrics.server import SystemMetrics
from app.testing.benchmark.observability import register_benchmark_observability

logging.getLogger("werkzeug").setLevel(logging.ERROR)

exit_event = threading.Event()
DEFAULT_ICAO = "KLAX"
BENCHMARK_PING_INTERVAL_S = 60
BENCHMARK_PING_TIMEOUT_S = 120

def create_app():
    mimetypes.add_type("application/javascript", ".js")

    app = Flask(__name__, static_url_path="/static", static_folder="static")
    CORS(app)

    async_mode = "eventlet"
    benchmark_mode = os.getenv("CPDLC_BENCHMARK") == "1"

    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        async_mode=async_mode,
        transports=["websocket"],
        ping_interval=BENCHMARK_PING_INTERVAL_S if benchmark_mode else 25,
        ping_timeout=BENCHMARK_PING_TIMEOUT_S if benchmark_mode else 20,
    )

    return app, socketio


def signal_handler(sig, frame):
    print("\n[System] Ctrl+C detected, exiting...")
    exit_event.set()
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)

    parser = argparse.ArgumentParser()
    parser.add_argument("--icao", "--ICAO", default=DEFAULT_ICAO)
    args = parser.parse_args()

    selected_icao: str = args.icao.upper()

    app, socketio = create_app()

    airport_map_manager = AirportMapManager(selected_icao)
    metrics_store = SystemMetrics()

    socket_service = SocketService(socketio, metrics_store)
    pilot_manager = PilotManager(airport_map_manager=airport_map_manager)
    atc_manager = AtcManager(selected_icao)

    general.pilot_manager = pilot_manager
    general.socket_service = socket_service
    app.register_blueprint(general.general_bp)

    socket_manager = SocketManager(
        socket_service=socket_service,
        pilot_manager=pilot_manager,
        atc_manager=atc_manager,
        airport_map_manager=airport_map_manager,
        metrics_store=metrics_store,
    )

    socket_manager.init_events()

    if os.getenv("CPDLC_BENCHMARK") == "1":
        register_benchmark_observability(
            app=app,
            pilot_manager=pilot_manager,
            atc_manager=atc_manager,
            metrics_store=metrics_store,
        )

    try:
        port = 5321
        print(f"[SERVER] Server running at http://localhost:{port}")

        if os.getenv("CPDLC_BENCHMARK") == "1":
            print("[SERVER] Benchmark observability enabled.")

        allow_unsafe = socketio.async_mode == "threading"

        socketio.run(
            app,
            host="0.0.0.0",
            port=port,
            use_reloader=False,
            allow_unsafe_werkzeug=allow_unsafe,
        )

    except KeyboardInterrupt:
        pass