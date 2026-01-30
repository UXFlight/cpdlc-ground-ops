try:
    import eventlet  # type: ignore
    eventlet.monkey_patch()
except Exception:
    eventlet = None

import threading
import signal
import sys
import mimetypes
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from app.classes.socket import SocketService
from app.managers import PilotManager, SocketManager, AtcManager, AirportMapManager
from app.testing.observability.system_metrics import SystemMetrics
from app.testing.observability.system_snapshot import register_system_snapshot
from app.routes import general

from app.classes.agent import Echo

exit_event = threading.Event()

def create_app():
    mimetypes.add_type('application/javascript', '.js')
    app = Flask(__name__, static_url_path="/static", static_folder="static")
    CORS(app)
    async_mode = "eventlet" if eventlet else "threading"
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        async_mode=async_mode,
        transports=["websocket"],
    )
    return app, socketio

def signal_handler(sig, frame):
    print("\n[System] Ctrl+C detected, exiting...")
    exit_event.set()
    sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)

    app, socketio = create_app()

    import logging
    logging.getLogger('werkzeug').setLevel(logging.ERROR)

    # agent = Echo()
    # Echo.start_ingescape_agent() #! to start ingescape agent
    
    airport_map_manager = AirportMapManager()
    metrics_store = SystemMetrics()
    socket_service = SocketService(socketio, metrics_store)
    pilot_manager = PilotManager(airport_map_manager=airport_map_manager)
    atc_manager = AtcManager()

    general.pilot_manager = pilot_manager
    general.socket_service = socket_service
    app.register_blueprint(general.general_bp)

    socket_manager = SocketManager(
        socket_service=socket_service, 
        pilot_manager=pilot_manager, 
        atc_manager=atc_manager,
        airport_map_manager=airport_map_manager,
        metrics_store=metrics_store
    )
    
    socket_manager.init_events()
    register_system_snapshot(app, pilot_manager, atc_manager, metrics_store)
    

    try:
        host = "0.0.0.0"
        port = 5321
        print(f"[SERVER] Server running at http://localhost:{port}")
        allow_unsafe = socketio.async_mode == "threading"
        socketio.run(app, host="0.0.0.0", port=5321, use_reloader=False, allow_unsafe_werkzeug=allow_unsafe)
    except KeyboardInterrupt:
        pass
