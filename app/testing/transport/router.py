from typing import Optional

from flask_socketio import SocketIO

from ..core.constants import (
    ATC_ROOM,
    EVENT_ATC_MESSAGE,
    EVENT_PILOT_MESSAGE,
    EVENT_PILOT_STATE,
    ROLE_ATC,
    ROLE_PILOT,
)
from ..core.models import Message, now_ts
from ..core.state import StateStore
from ..observability.metrics import MetricsStore


class Router:
    def __init__(self, socketio: SocketIO, state_store: StateStore,
                 metrics_store: MetricsStore) -> None:
        self._socketio = socketio
        self._state = state_store
        self._metrics = metrics_store

    def from_pilot(self, pilot_id: str, body: str,
                   client_sent_ts: Optional[float]) -> None:
        message = Message.create(ROLE_PILOT, ROLE_ATC, pilot_id, body, client_sent_ts)
        payload = message.to_dict()
        self._state.add_pilot_message(pilot_id, payload)
        self._socketio.emit(EVENT_ATC_MESSAGE, payload, room=ATC_ROOM)
        self._socketio.emit(EVENT_PILOT_STATE,
                            self._state.get_pilot_state_data(pilot_id),
                            room=pilot_id)
        self._metrics.record_delivery(ROLE_ATC, pilot_id)
        self._metrics.record_message(message.from_role, message.server_received_ts,
                                     now_ts(), message.client_sent_ts)

    def from_atc(self, pilot_id: str, body: str,
                 client_sent_ts: Optional[float]) -> None:
        message = Message.create(ROLE_ATC, ROLE_PILOT, pilot_id, body, client_sent_ts)
        payload = message.to_dict()
        self._state.add_pilot_message(pilot_id, payload)
        self._socketio.emit(EVENT_PILOT_MESSAGE, payload, room=pilot_id)
        self._socketio.emit(EVENT_PILOT_STATE,
                            self._state.get_pilot_state_data(pilot_id),
                            room=pilot_id)
        self._metrics.record_delivery(ROLE_PILOT, pilot_id)
        self._metrics.record_message(message.from_role, message.server_received_ts,
                                     now_ts(), message.client_sent_ts)
