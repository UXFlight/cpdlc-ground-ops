import threading
import time

import socketio

from app.utils.constants import DEFAULT_STEPS


class SystemLoadClient:
    def __init__(self, role: str, server_url: str,
                 interval_s: float, duration_s: float) -> None:
        self.role = role
        self.server_url = server_url
        self.interval_s = interval_s
        self.duration_s = duration_s
        self._sio = socketio.Client(reconnection=False, logger=False,
                                    engineio_logger=False)
        self._queue = []
        self._queue_lock = threading.Lock()
        self._in_flight = False
        self._last_send_ts = 0.0
        self._step_code = DEFAULT_STEPS[1]["requestType"]

        @self._sio.on("new_request")
        def _new_request(data):
            if self.role != "atc":
                return
            with self._queue_lock:
                self._queue.append(data)

        @self._sio.on("atcResponse")
        def _atc_response(data):
            if self.role != "pilot":
                return
            self._in_flight = False
            payload = {
                "action": "wilco",
                "requestType": data.get("step_code"),
                "client_sent_ts": time.time(),
            }
            self._safe_emit("sendAction", payload)

    def start(self) -> None:
        auth = {"r": 0} if self.role == "pilot" else {"r": 1}
        try:
            self._sio.connect(self.server_url, transports=["polling"], auth=auth)
        except Exception:
            return
        end_ts = time.time() + self.duration_s
        while time.time() < end_ts:
            if self.role == "pilot":
                self._pilot_tick()
            else:
                self._atc_tick()
            time.sleep(self.interval_s)
        self._sio.disconnect()

    def _pilot_tick(self) -> None:
        if not self._in_flight:
            payload = {"requestType": self._step_code, "client_sent_ts": time.time()}
            self._safe_emit("sendRequest", payload)
            self._in_flight = True
            self._last_send_ts = time.time()
            return
        if time.time() - self._last_send_ts > 2.0:
            payload = {"requestType": self._step_code, "client_sent_ts": time.time()}
            self._safe_emit("cancelRequest", payload)
            self._in_flight = False

    def _atc_tick(self) -> None:
        item = None
        with self._queue_lock:
            if self._queue:
                item = self._queue.pop(0)
        if not item:
            return
        payload = {
            "pilot_sid": item.get("pilot_sid"),
            "step_code": item.get("step_code"),
            "request_id": item.get("request_id"),
            "action": "affirm",
            "message": "ack",
            "client_sent_ts": time.time(),
        }
        self._safe_emit("atcResponse", payload)

    def _safe_emit(self, event: str, payload: dict) -> None:
        try:
            if self._sio.connected:
                self._sio.emit(event, payload)
        except Exception:
            return
