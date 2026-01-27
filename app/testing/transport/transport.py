from typing import Any, Dict
from flask import request
from flask_socketio import SocketIO, emit, join_room, leave_room
from .connections import ConnectionRegistry
from ..core.constants import (
    ATC_ROOM,
    EVENT_ATC_MESSAGE,
    EVENT_ATC_STATE,
    EVENT_ERROR,
    EVENT_GET_STATE,
    EVENT_PILOT_MESSAGE,
    EVENT_PILOT_STATE,
    EVENT_REGISTER,
    EVENT_REGISTERED,
    ROLE_ATC,
    ROLE_PILOT,
    ROLES,
)
from ..observability.metrics import MetricsStore
from .router import Router
from ..core.state import StateStore
def register_handlers(socketio: SocketIO, state_store: StateStore,
                      metrics_store: MetricsStore, router: Router) -> None:
    registry = ConnectionRegistry()
    @socketio.on("connect")
    def on_connect() -> None:
        emit(EVENT_REGISTERED, {"status": "connected"})

    @socketio.on("disconnect")
    def on_disconnect() -> None:
        role, pilot_id = registry.unregister(request.sid)
        if role == ROLE_PILOT and pilot_id:
            leave_room(pilot_id)
            state_store.unregister_pilot(pilot_id)
            socketio.emit(EVENT_ATC_STATE, state_store.get_atc_state_data(),
                          room=ATC_ROOM)
        if role == ROLE_ATC:
            leave_room(ATC_ROOM)

    @socketio.on(EVENT_REGISTER)
    def on_register(data: Dict[str, Any]) -> None:
        role = data.get("role")
        client_id = data.get("client_id")
        if role not in ROLES or not client_id:
            metrics_store.record_error()
            emit(EVENT_ERROR, {"error": "invalid_registration"})
            return
        if role == ROLE_PILOT:
            registry.register(request.sid, role, client_id)
            join_room(client_id)
            state_store.register_pilot(client_id)
            emit(EVENT_PILOT_STATE, state_store.get_pilot_state_data(client_id))
            socketio.emit(EVENT_ATC_STATE, state_store.get_atc_state_data(),
                          room=ATC_ROOM)
        if role == ROLE_ATC:
            registry.register(request.sid, role, None)
            join_room(ATC_ROOM)
            emit(EVENT_ATC_STATE, state_store.get_atc_state_data())
        emit(EVENT_REGISTERED, {"role": role, "client_id": client_id})

    @socketio.on(EVENT_GET_STATE)
    def on_get_state() -> None:
        role = registry.get_role(request.sid)
        if role == ROLE_PILOT:
            pilot_id = registry.get_pilot_id(request.sid)
            emit(EVENT_PILOT_STATE, state_store.get_pilot_state_data(pilot_id))
            return
        if role == ROLE_ATC:
            emit(EVENT_ATC_STATE, state_store.get_atc_state_data())
            return
        metrics_store.record_error()
        emit(EVENT_ERROR, {"error": "unknown_role"})

    @socketio.on(EVENT_PILOT_MESSAGE)
    def on_pilot_message(data: Dict[str, Any]) -> None:
        if registry.get_role(request.sid) != ROLE_PILOT:
            metrics_store.record_error()
            emit(EVENT_ERROR, {"error": "role_not_pilot"})
            return
        pilot_id = registry.get_pilot_id(request.sid)
        body = data.get("body")
        if not pilot_id or not body:
            metrics_store.record_error()
            emit(EVENT_ERROR, {"error": "invalid_message"})
            return
        router.from_pilot(pilot_id, body, data.get("client_sent_ts"))

    @socketio.on(EVENT_ATC_MESSAGE)
    def on_atc_message(data: Dict[str, Any]) -> None:
        if registry.get_role(request.sid) != ROLE_ATC:
            metrics_store.record_error()
            emit(EVENT_ERROR, {"error": "role_not_atc"})
            return
        pilot_id = data.get("pilot_id")
        body = data.get("body")
        if not pilot_id or not body:
            metrics_store.record_error()
            emit(EVENT_ERROR, {"error": "invalid_message"})
            return
        router.from_atc(pilot_id, body, data.get("client_sent_ts"))
