from __future__ import annotations
import socketio
from threading import Event
from typing import Callable, Any
from app.testing.benchmark.clients.logging import build_null_logger
from app.testing.benchmark.metrics.latency import ClientLatencyTracker
from app.utils.constants import ENGINE_STARTUP, WILCO
from app.utils.socket_constants import (
    ACTION_ACK_SEND,
    ATC_RESPONSE_TO_PILOT,
    CONNECTED_TO_ATC_SEND,
    ERROR_SEND,
    SEND_ACTION_LISTEN,
    SEND_REQUEST_LISTEN,
)


class PilotBenchmarkClient:
    def __init__(
        self,
        client_id: str,
        server_url: str,
        latency_tracker: ClientLatencyTracker,
        message_id_factory: Callable[[str], str],
        request_type: str = ENGINE_STARTUP,
    ) -> None:
        self.client_id = client_id
        self.server_url = server_url
        self.latency_tracker = latency_tracker
        self.message_id_factory = message_id_factory
        self.request_type = request_type

        self.connected = False
        self.server_sid: str | None = None

        self.sent_requests = 0
        self.sent_actions = 0
        self.completed_cycles = 0
        self.errors: list[Any] = []

        self._connected_to_atc_event = Event()
        self._ready_for_next_request = Event()
        self._ready_for_next_request.set()

        self.sio = socketio.Client(
            reconnection=False,
            logger=False,
            engineio_logger=build_null_logger(f"benchmark.engineio.pilot.{client_id}"),
        )

        self._register_handlers()

    def _register_handlers(self) -> None:
        @self.sio.event
        def connect():
            self.connected = True

        @self.sio.event
        def disconnect():
            self.connected = False

        @self.sio.on(CONNECTED_TO_ATC_SEND)
        def on_connected_to_atc(data):
            if isinstance(data, dict):
                self.server_sid = data.get("sid") or data.get("pilotSid")
            self._connected_to_atc_event.set()

        @self.sio.on(ATC_RESPONSE_TO_PILOT)
        def on_atc_response(data):
            self._handle_atc_response(data)

        @self.sio.on(ACTION_ACK_SEND)
        def on_action_ack(data):
            self.completed_cycles += 1
            self._ready_for_next_request.set()

        @self.sio.on(ERROR_SEND)
        def on_error(data):
            self.errors.append(data)
            self._ready_for_next_request.set()

    def connect(self, timeout_s: float) -> bool:
        try:
            self.sio.connect(
                self.server_url,
                auth={"r": 0},
                transports=["websocket"],
                wait_timeout=timeout_s,
            )
            return self._connected_to_atc_event.wait(timeout_s)
        except Exception as exc:
            self.errors.append({"connect_error": str(exc)})
            return False

    def disconnect(self) -> None:
        try:
            if self.sio.connected:
                self.sio.disconnect()
        except Exception as exc:
            self.errors.append({"disconnect_error": str(exc)})

    def is_ready(self) -> bool:
        return self.connected and self._ready_for_next_request.is_set()

    def send_request(self) -> bool:
        if not self.is_ready():
            return False

        self._ready_for_next_request.clear()

        message_id = self.message_id_factory(f"{self.client_id}_pilot_request")

        payload = {
            "requestType": self.request_type,
            "test_message_id": message_id,
        }

        try:
            self.latency_tracker.mark_sent(message_id)
            self.sio.emit(SEND_REQUEST_LISTEN, payload)
            self.sent_requests += 1
            return True
        except Exception as exc:
            self.errors.append({"send_request_error": str(exc)})
            self._ready_for_next_request.set()
            return False

    def send_wilco(self, request_type: str) -> bool:
        message_id = self.message_id_factory(f"{self.client_id}_pilot_wilco")

        payload = {
            "requestType": request_type,
            "action": WILCO,
            "test_message_id": message_id,
        }

        try:
            self.latency_tracker.mark_sent(message_id)
            self.sio.emit(SEND_ACTION_LISTEN, payload)
            self.sent_actions += 1
            return True
        except Exception as exc:
            self.errors.append({"send_wilco_error": str(exc)})
            self._ready_for_next_request.set()
            return False

    def _handle_atc_response(self, data: dict) -> None:
        if not isinstance(data, dict):
            return

        test_message_id = data.get("test_message_id")
        if test_message_id:
            self.latency_tracker.mark_received_once(test_message_id)

        step_code = data.get("step_code")
        if not step_code:
            self.errors.append({
                "error": "missing_step_code_in_atc_response",
                "payload": data,
            })
            self._ready_for_next_request.set()
            return

        self.send_wilco(step_code)