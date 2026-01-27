import threading
import time
import socketio
from app.utils.constants import DEFAULT_STEPS, ACTION_DEFINITIONS
from app.utils.types import StepStatus
ACTION_WILCO = "wilco" if "wilco" in ACTION_DEFINITIONS else "wilco"
class SystemLoadClient:
    def __init__(self, role: str, server_url: str, interval_s: float, duration_s: float, atc_index: int = 0, atc_total: int = 1) -> None:
        self.role = role
        self.server_url = server_url
        self.interval_s = interval_s
        self.duration_s = duration_s
        self._sio = socketio.Client(reconnection=False, logger=False, engineio_logger=False)
        self._queue = []
        self._queue_lock = threading.Lock()
        self._phase = "idle"
        self._last_send_ts = 0.0
        self._step_code = DEFAULT_STEPS[1]["requestType"]
        self._seen = set()
        self._atc_index, self._atc_total = atc_index, max(atc_total, 1)
        @self._sio.on("requestAcknowledged")
        def _request_ack(data):
            if self.role == "pilot" and self._phase == "pending_request": self._phase = "requested"
        @self._sio.on("new_request")
        def _new_request(data):
            if self.role != "atc": return
            if data.get("status") != StepStatus.NEW.value: return
            key = self._queue_key(data)
            if key in self._seen: return
            self._seen.add(key)
            with self._queue_lock: self._queue.append(data)
        @self._sio.on("pilot_list")
        def _pilot_list(data):
            if self.role != "atc": return
            for pilot in data or []:
                sid = pilot.get("sid")
                for code, step in (pilot.get("steps") or {}).items():
                    status = step.get("status")
                    if status == StepStatus.NEW.value:
                        req_id = step.get("request_id")
                        if sid and req_id:
                            item = {"pilot_sid": sid, "step_code": code, "request_id": req_id,
                                    "validated_at": step.get("validated_at"), "status": status}
                            key = self._queue_key(item)
                            if key in self._seen: continue
                            self._seen.add(key)
                            with self._queue_lock: self._queue.append(item)
        @self._sio.on("atcResponse")
        def _atc_response(data):
            if self.role != "pilot" or self._phase not in {"pending_request", "requested"}: return
            self._phase = "action_sent"
            payload = {"action": ACTION_WILCO, "requestType": data.get("step_code"), "client_sent_ts": time.time()}
            self._safe_emit("sendAction", payload)
        @self._sio.on("actionAcknowledged")
        def _action_ack(data):
            if self.role == "pilot": self._phase = "idle"
        @self._sio.on("error")
        def _error(data):
            if self.role != "pilot": return
            msg = str(data.get("message") or data.get("payload", {}).get("message") or "") if isinstance(data, dict) else ""
            if "already in progress" in msg: self._phase = "requested"
            elif self._phase == "pending_request": self._phase = "idle"
    def start(self) -> None:
        auth = {"r": 0} if self.role == "pilot" else {"r": 1}
        try:
            self._sio.connect(self.server_url, transports=["polling"], auth=auth)
        except Exception:
            return
        if self.role == "atc":
            self._safe_emit("getPilotList", None)
        end_ts = time.time() + self.duration_s
        while time.time() < end_ts:
            self._pilot_tick() if self.role == "pilot" else self._atc_tick()
            time.sleep(self.interval_s)
        self._sio.disconnect()
    def _pilot_tick(self) -> None:
        if self._phase == "idle":
            payload = {"requestType": self._step_code, "client_sent_ts": time.time()}
            self._safe_emit("sendRequest", payload)
            self._phase = "pending_request"
            self._last_send_ts = time.time()
            return
        if self._phase == "pending_request" and time.time() - self._last_send_ts > 90.0: self._phase = "idle"
    def _atc_tick(self) -> None:
        item = None
        with self._queue_lock:
            if self._queue: item = self._queue.pop(0)
        if not item: return
        sid = item.get("pilot_sid")
        if self._atc_total > 1 and sid:
            if sum(ord(c) for c in sid) % self._atc_total != self._atc_index: return
        payload = {"pilot_sid": sid, "step_code": item.get("step_code"), "request_id": item.get("request_id"),
                   "action": "affirm", "message": "ack", "client_sent_ts": time.time()}
        self._safe_emit("atcResponse", payload)
    def _queue_key(self, item: dict) -> tuple: return (item.get("pilot_sid"), item.get("step_code"),
                                                       item.get("validated_at"), item.get("request_id"), item.get("status"))
    def _safe_emit(self, event: str, payload: dict | None) -> None:
        try:
            if self._sio.connected: self._sio.emit(event) if payload is None else self._sio.emit(event, payload)
        except Exception: return
