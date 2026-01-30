import threading
import time
import socketio
from app.utils.constants import DEFAULT_STEPS, ACTION_DEFINITIONS
from app.utils.types import StepStatus

ROLE_PILOT = "pilot"
ROLE_ATC = "atc"
PHASE_IDLE = "idle"
PHASE_PENDING = "pending_request"
PHASE_REQUESTED = "requested"
PHASE_ACTION_SENT = "action_sent"
ACTION_WILCO = "wilco" if "wilco" in ACTION_DEFINITIONS else "wilco"
ACTION_AFFIRM = "affirm"

class SystemLoadClient:
    def __init__(self, 
                    role: str, 
                    server_url: str, 
                    interval_s: float, 
                    duration_s: float, 
                    atc_index: int = 0,
                    atc_total: int = 1, 
                    start_event: threading.Event | None = None,
                    client_id: str | None = None
                 ) -> None:
        self.role = role
        self.server_url = server_url
        self.interval_s = interval_s
        self.duration_s = duration_s
        self._sio = socketio.Client(reconnection=False, logger=False, engineio_logger=False)
        self._queue = []
        self._queue_lock = threading.Lock()
        self._phase = PHASE_IDLE
        self._last_send_ts = 0.0
        self._step_code = DEFAULT_STEPS[1]["requestType"]
        self._seen = set()
        self._atc_index, self._atc_total = atc_index, max(atc_total, 1)
        self._start_event = start_event
        self._client_id = client_id or ""
        self.completed_cycles = 0
        self.unexpected_events: list[str] = []
        self.request_acks = 0
        self.atc_responses = 0
        self.action_acks = 0

        @self._sio.on("requestAcknowledged")
        def _request_ack(data):
            if self.role != ROLE_PILOT:
                return
            if self._phase == PHASE_PENDING:
                self._phase = PHASE_REQUESTED
                self.request_acks += 1
            else:
                self.unexpected_events.append("request_ack_unexpected")

        @self._sio.on("new_request")
        def _new_request(data):
            if self.role != ROLE_ATC: return
            if data.get("status") != StepStatus.NEW.value: return
            key = self._queue_key(data)
            if key in self._seen: return
            self._seen.add(key)
            with self._queue_lock: self._queue.append(data)

        @self._sio.on("pilot_list")
        def _pilot_list(data):
            if self.role != ROLE_ATC: return
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
            if self.role != ROLE_PILOT:
                return
            if self._phase not in {PHASE_PENDING, PHASE_REQUESTED}:
                self.unexpected_events.append("atc_response_unexpected")
                return
            self._phase = PHASE_ACTION_SENT
            self.atc_responses += 1
            payload = {"action": ACTION_WILCO, "requestType": data.get("step_code"), "client_sent_ts": time.time()}
            self._safe_emit("sendAction", payload)

        @self._sio.on("actionAcknowledged")
        def _action_ack(data):
            if self.role != ROLE_PILOT:
                return
            if self._phase == PHASE_ACTION_SENT:
                self._phase = PHASE_IDLE
                self.action_acks += 1
                self.completed_cycles += 1
            else:
                self.unexpected_events.append("action_ack_unexpected")

        @self._sio.on("error")
        def _error(data):
            if self.role != ROLE_PILOT:
                return
            msg = str(data.get("message") or data.get("payload", {}).get("message") or "") if isinstance(data, dict) else ""
            if "already in progress" in msg:
                self._phase = PHASE_REQUESTED
            elif self._phase == PHASE_PENDING:
                self._phase = PHASE_IDLE

    def start(self) -> None:
        auth = {"r": 0} if self.role == ROLE_PILOT else {"r": 1}
        try:
            self._sio.connect(self.server_url, transports=["polling"], auth=auth)
        except Exception:
            return
        if self.role == ROLE_ATC:
            self._safe_emit("getPilotList", None)
        if self._start_event:
            self._start_event.wait()
        end_ts = time.time() + self.duration_s
        while time.time() < end_ts:
            self._pilot_tick() if self.role == ROLE_PILOT else self._atc_tick()
            time.sleep(self.interval_s)
        self._sio.disconnect()

    def _pilot_tick(self) -> None:
        if self._phase == PHASE_IDLE:
            payload = {"requestType": self._step_code, "client_sent_ts": time.time()}
            if self._client_id:
                payload["client_tag"] = self._client_id
            self._safe_emit("sendRequest", payload)
            self._phase = PHASE_PENDING
            self._last_send_ts = time.time()
            return
        if self._phase == PHASE_PENDING and time.time() - self._last_send_ts > 90.0:
            self._phase = PHASE_IDLE
    
    def _atc_tick(self) -> None:
        item = None
        with self._queue_lock:
            if self._queue: item = self._queue.pop(0)
        if not item: return
        sid = item.get("pilot_sid")
        if self._atc_total > 1 and sid:
            if sum(ord(c) for c in sid) % self._atc_total != self._atc_index: return
        payload = {"pilot_sid": sid, "step_code": item.get("step_code"), "request_id": item.get("request_id"),
                   "action": ACTION_AFFIRM, "message": "ack", "client_sent_ts": time.time()}
        self._safe_emit("atcResponse", payload)
    
    def _queue_key(self, item: dict) -> tuple: return (item.get("pilot_sid"), item.get("step_code"),
                                                       item.get("validated_at"), item.get("request_id"), item.get("status"))
    
    def _safe_emit(self, event: str, payload: dict | None) -> None:
        try:
            if self._sio.connected: self._sio.emit(event) if payload is None else self._sio.emit(event, payload)
        except Exception: return

    def stats(self) -> dict:
        return {
            "client_id": self._client_id,
            "completed_cycles": self.completed_cycles,
            "unexpected_events": list(self.unexpected_events),
            "request_acks": self.request_acks,
            "atc_responses": self.atc_responses,
            "action_acks": self.action_acks,
        }
