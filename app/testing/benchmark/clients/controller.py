from __future__ import annotations
import socketio
from threading import Event
from typing import Callable, Any
from app.testing.benchmark.metrics.latency import ClientLatencyTracker
from app.utils.constants import AFFIRM
from app.utils.socket_constants import (
    ATC_RESPONSE_LISTEN,
    ERROR_SEND,
    NEW_REQUEST_SEND,
)

class ControllerBenchmarkClient:
    def __init__(
        self,
        client_id: str,
        server_url: str,
        latency_tracker: ClientLatencyTracker,
        message_id_factory: Callable[[str], str],
        can_respond: bool,
    ) -> None:
        self.client_id = client_id
        self.server_url = server_url
        self.latency_tracker = latency_tracker
        self.message_id_factory = message_id_factory
        self.can_respond = can_respond

        self.connected = False
        self.received_requests = 0
        self.sent_responses = 0
        self.errors: list[Any] = []

        self._connected_event = Event()
        self.sio = socketio.Client(
            reconnection=False,
            logger=False,
            engineio_logger=False,
        )

        self._register_handlers()

    def _register_handlers(self) -> None:
        @self.sio.event
        def connect():
            self.connected = True
            self._connected_event.set()

        @self.sio.event
        def disconnect():
            self.connected = False

        @self.sio.on(NEW_REQUEST_SEND)
        def on_new_request(data):
            self._handle_new_request(data)

        @self.sio.on(ERROR_SEND)
        def on_error(data):
            self.errors.append(data)

    def connect(self, timeout_s: float) -> bool:
        try:
            self.sio.connect(
                self.server_url,
                auth={"r": 1},
                transports=["websocket"],
                wait_timeout=timeout_s,
            )
            return self._connected_event.wait(timeout_s)
        except Exception as exc:
            self.errors.append({"connect_error": str(exc)})
            return False

    def disconnect(self) -> None:
        try:
            if self.sio.connected:
                self.sio.disconnect()
        except Exception as exc:
            self.errors.append({"disconnect_error": str(exc)})

    def _handle_new_request(self, data: dict) -> None:
        if not isinstance(data, dict):
            return

        test_message_id = data.get("test_message_id")
        if test_message_id:
            self.latency_tracker.mark_received_once(test_message_id)

        self.received_requests += 1

        if not self.can_respond:
            return

        status = data.get("status")
        if status not in {"new", "requested"}:
            return

        pilot_sid = data.get("pilot_sid")
        step_code = data.get("step_code")
        request_id = data.get("request_id")

        if not pilot_sid or not step_code or not request_id:
            self.errors.append({
                "error": "missing_request_payload_fields",
                "payload": data,
            })
            return

        self.send_affirm_response(
            pilot_sid=pilot_sid,
            step_code=step_code,
            request_id=request_id,
        )

    def send_affirm_response(
        self,
        pilot_sid: str,
        step_code: str,
        request_id: str,
    ) -> None:
        message_id = self.message_id_factory(f"{self.client_id}_atc_response")

        payload = {
            "pilot_sid": pilot_sid,
            "step_code": step_code,
            "action": AFFIRM,
            "message": "AFFIRM",
            "request_id": request_id,
            "test_message_id": message_id,
        }

        try:
            self.latency_tracker.mark_sent(message_id)
            self.sio.emit(ATC_RESPONSE_LISTEN, payload)
            self.sent_responses += 1
        except Exception as exc:
            self.errors.append({"send_response_error": str(exc)})