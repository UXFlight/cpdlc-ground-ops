from flask import request
from typing import TYPE_CHECKING, Any
from app.utils.constants import CANCEL, CLEARANCE_CODES, EXPECTED_TAXI_CLEARANCE, TAXI_CLEARANCE, UNABLE
from app.utils.parse import interpolate_request_message, parse_status
from app.utils.socket_constants import (
    ACTION_ACK_SEND,
    ACTIVITY_INFO_SEND,
    AIRPORT_MAP_DATA_SEND,
    ATC_LIST_SEND,
    ATC_RESPONSE_LISTEN,
    ATC_RESPONSE_TO_PILOT,
    ATC_ROOM,
    CANCEL_CLEARANCE_LISTEN,
    CANCEL_REQUEST_LISTEN,
    CLEARANCE_CANCELLED,
    CONNECT_LISTEN,
    CONNECTED_TO_ATC_SEND,
    DISCONNECT_LISTEN,
    ERROR_SEND,
    GET_ACTIVITY_LISTEN,
    GET_AIRPORT_MAP_DATA_LISTEN,
    GET_CLEARANCE_LISTEN,
    GET_PILOTS_LISTEN,
    NEW_REQUEST_SEND,
    PILOT_CONNECTED_SEND,
    PILOT_DISCONNECTED_SEND,
    PILOT_LIST_SEND,
    PROPOSED_CLEARANCE_SEND,
    REQUEST_ACK_SEND,
    REQUEST_CANCELLED_SEND,
    SEND_ACTION_LISTEN,
    SEND_REQUEST_LISTEN,
)
from app.utils.time_utils import get_current_timestamp, get_formatted_time
from app.utils.types import Clearance, ClearanceType, PilotConnectInfo, PilotPublicView, SocketErrorPayload, StepStatus, UpdateStepData
from app.managers.log_manager import logger
from app.classes.clearance import ClearanceEngine

if TYPE_CHECKING:
    from app.classes.pilot import Pilot
    from app.classes.socket import SocketService
    from app.managers.pilot_manager import PilotManager
    from app.managers.atc_manager import AtcManager
    from app.managers.airport_map_manager import AirportMapManager
    from app.testing.observability.system_metrics import SystemMetrics


class SocketManager:
    def __init__(
        self,
        socket_service: "SocketService",
        pilot_manager: "PilotManager",
        atc_manager: "AtcManager",
        airport_map_manager: "AirportMapManager",
        metrics_store: "SystemMetrics",
    ):
        self.socket: "SocketService" = socket_service
        self.pilots: "PilotManager" = pilot_manager
        self.atc_manager: "AtcManager" = atc_manager
        self.airport_map_manager: "AirportMapManager" = airport_map_manager
        self.clearance_engine = ClearanceEngine(airport_map_manager.map_data)
        self.metrics: "SystemMetrics" = metrics_store
        self._disconnecting: set[str] = set()

    def _emit(self, room: str, event: str, payload: Any, **kwargs) -> None:
        self.socket.send(event, payload, room=room, **kwargs)

    def init_events(self):
        self.socket.listen(CONNECT_LISTEN, self.on_connect)
        self.socket.listen(DISCONNECT_LISTEN, self.on_disconnect)

        # PILOT EVENTS
        self.socket.listen(SEND_REQUEST_LISTEN, self.on_send_request)
        self.socket.listen(CANCEL_REQUEST_LISTEN, self.on_cancel_request)
        self.socket.listen(SEND_ACTION_LISTEN, self.on_action_event)
        self.socket.listen(GET_ACTIVITY_LISTEN, self.on_activity_request)

        # ATC EVENTS
        self.socket.listen(GET_PILOTS_LISTEN, self.handle_pilot_list)
        self.socket.listen(GET_AIRPORT_MAP_DATA_LISTEN, self.handle_map_request)
        self.socket.listen(GET_CLEARANCE_LISTEN, self.on_clearance_request)
        self.socket.listen(CANCEL_CLEARANCE_LISTEN, self.on_clearance_cancel)

        # GLOBAL EVENTS
        self.socket.listen(ATC_RESPONSE_LISTEN, self.on_atc_response)

    ## PILOT UIS EVENTS
    ## === CONNECT
    def on_connect(self, auth=None):
        sid = request.sid
        role = auth.get("r") if auth else None  # 0 = pilot, 1 = atc

        if role == 0:
            public_view: PilotPublicView = self.pilots.create(sid)
            logger.log_event(pilot_id=sid, event_type="SOCKET", message=f"Pilot connected: {sid}")

            connected_payload: PilotConnectInfo = {
                "facility": self.atc_manager.connection_info["facility"],
                "connectedSince": self.atc_manager.connection_info["connectedSince"],
                "sid": sid,
            }
            self._emit(sid, CONNECTED_TO_ATC_SEND, connected_payload)

            if self.atc_manager.has_any():
                self._emit(ATC_ROOM, PILOT_CONNECTED_SEND, public_view)

        elif role == 1:
            self.atc_manager.create(sid)
            self.socket.enter_room(sid, room=ATC_ROOM)
            logger.log_event(pilot_id=sid, event_type="SOCKET", message=f"ATC connected: {sid}")

            pilot_list_data = self.get_adjusted_pilot_list()
            self._emit(sid, PILOT_LIST_SEND, pilot_list_data)

            atc_list = self.atc_manager.get_all()
            self._emit(ATC_ROOM, ATC_LIST_SEND, atc_list)

        else:
            logger.log_event(pilot_id=sid, event_type="SOCKET", message="Unknown role -- disconnecting")
            self.socket.disconnect(sid)

    def on_disconnect(self, data=None):
        sid = request.sid
        if sid in self._disconnecting:
            return
        self._disconnecting.add(sid)

        try:
            if self.pilots.exists(sid):
                self.pilots.remove(sid)
                logger.log_event(pilot_id=sid, event_type="SOCKET", message=f"Pilot disconnected: {sid}")

                if self.atc_manager.has_any():
                    try:
                        self._emit(ATC_ROOM, PILOT_DISCONNECTED_SEND, sid)
                    except Exception as e:
                        logger.log_error(pilot_id=sid, context="DISCONNECT", error=str(e))

            elif self.atc_manager.exists(sid):
                self.atc_manager.remove(sid)
                self.socket.leave_room(sid, room=ATC_ROOM)
                atc_list = self.atc_manager.get_all()
                try:
                    self._emit(ATC_ROOM, ATC_LIST_SEND, atc_list, skip_sid=sid)
                except Exception as e:
                    logger.log_error(pilot_id=sid, context="DISCONNECT", error=str(e))
                logger.log_event(pilot_id=sid, event_type="SOCKET", message=f"ATC disconnected: {sid}")

            else:
                logger.log_event(pilot_id=sid, event_type="SOCKET", message="Unknown SID disconnected")
        finally:
            self._disconnecting.discard(sid)

    ## === SEND REQUESTS
    def on_send_request(self, data: dict):
        sid = request.sid
        pilot: Pilot = self.pilots.get(sid)
        start_ts = get_current_timestamp()

        try:
            request_type = data.get("requestType")

            override: tuple[UpdateStepData, Clearance] | None = pilot.override_pending_expected_taxi(request_type)

            if override:
                overridden_update, cleared_clearance = override

                if request_type == TAXI_CLEARANCE:
                    self._emit(sid, ACTION_ACK_SEND, overridden_update.to_ack_payload())

                    self._emit(ATC_ROOM, NEW_REQUEST_SEND, overridden_update.to_atc_payload())

                    self._emit(sid, PROPOSED_CLEARANCE_SEND, {
                        "kind": cleared_clearance["kind"],
                        "instruction": cleared_clearance["instruction"],
                    })

                    self._emit(ATC_ROOM, PROPOSED_CLEARANCE_SEND, {
                        "pilot_sid": pilot.sid,
                        "clearance": cleared_clearance,
                    })

                elif request_type == EXPECTED_TAXI_CLEARANCE:
                    self._emit(sid, REQUEST_ACK_SEND, overridden_update.to_ack_payload())

                    self._emit(sid, PROPOSED_CLEARANCE_SEND, {
                        "kind": cleared_clearance["kind"],
                        "instruction": cleared_clearance["instruction"],
                    })

                    self.metrics.record_event(
                        "pilot",
                        start_ts,
                        get_current_timestamp(),
                        data.get("client_sent_ts"),
                    )
                    return

            step_payload: UpdateStepData = pilot.handle_send_request(data)
            step_code = step_payload.step_code

            self._emit(sid, REQUEST_ACK_SEND, step_payload.to_ack_payload())

            message = interpolate_request_message(step_code, pilot, data.get("direction"))
            step_payload.message = message

            status = parse_status(step_payload.status)
            step_payload.status = status

            if step_code in CLEARANCE_CODES:
                kind: ClearanceType = "expected" if step_code == EXPECTED_TAXI_CLEARANCE else "taxi"
                issued_at = get_formatted_time(get_current_timestamp())
                instruction, coords = self.clearance_engine.generate_clearance(pilot)

                clearance: Clearance = Clearance(
                    kind=kind,
                    instruction=instruction,
                    coords=coords,
                    issued_at=issued_at,
                )

                pilot.set_clearance(clearance)

                self._emit(ATC_ROOM, PROPOSED_CLEARANCE_SEND, {
                    "pilot_sid": pilot.sid,
                    "clearance": clearance,
                })

            self._emit(ATC_ROOM, NEW_REQUEST_SEND, step_payload.to_atc_payload())

            self.metrics.record_event(
                "pilot",
                start_ts,
                get_current_timestamp(),
                data.get("client_sent_ts"),
            )

        except Exception as e:
            error_payload: SocketErrorPayload = pilot._error("REQUEST", str(e), data.get("requestType"))
            self._emit(sid, ERROR_SEND, error_payload)
            logger.log_error(pilot_id=sid, context="REQUEST", error=str(e))
            self.metrics.record_error()

    ## === CANCEL REQUEST
    def on_cancel_request(self, data: dict):
        sid = request.sid
        pilot = self.pilots.get(sid)
        start_ts = get_current_timestamp()

        try:
            update_data: UpdateStepData = pilot.handle_cancel_request(data)

            self._emit(sid, REQUEST_CANCELLED_SEND, update_data.to_ack_payload())

            self._emit(ATC_ROOM, NEW_REQUEST_SEND, update_data.to_atc_payload())

            if update_data.step_code in CLEARANCE_CODES:
                clearance = pilot.clear_clearance(update_data.step_code)

                self._emit(ATC_ROOM, PROPOSED_CLEARANCE_SEND, {
                    "pilot_sid": pilot.sid,
                    "clearance": clearance,
                })

                self._emit(pilot.sid, PROPOSED_CLEARANCE_SEND, {
                    "kind": clearance["kind"],
                    "instruction": clearance["instruction"],
                })

            self.metrics.record_event(
                "pilot",
                start_ts,
                get_current_timestamp(),
                data.get("client_sent_ts"),
            )

        except Exception as e:
            error_payload: SocketErrorPayload = pilot._error("CANCEL", str(e), data.get("requestType"))
            self._emit(sid, ERROR_SEND, error_payload)
            logger.log_error(pilot_id=sid, context="CANCEL", error=str(e))
            self.metrics.record_error()

    ## === ACTION EVENTS
    def on_action_event(self, data: dict):
        sid = request.sid
        pilot = self.pilots.get(sid)
        start_ts = get_current_timestamp()

        try:
            update_data: UpdateStepData = pilot.process_action(data)

            self._emit(sid, ACTION_ACK_SEND, update_data.to_ack_payload())

            self._emit(ATC_ROOM, NEW_REQUEST_SEND, update_data.to_atc_payload())

            if data.get("action") in [CANCEL, UNABLE] and update_data.step_code in CLEARANCE_CODES:
                clearance = pilot.clear_clearance(update_data.step_code)

                self._emit(sid, PROPOSED_CLEARANCE_SEND, {
                    "kind": clearance["kind"],
                    "instruction": clearance["instruction"],
                })

                self._emit(ATC_ROOM, PROPOSED_CLEARANCE_SEND, {
                    "pilot_sid": pilot.sid,
                    "clearance": clearance,
                })

            self.metrics.record_event(
                "pilot",
                start_ts,
                get_current_timestamp(),
                data.get("client_sent_ts"),
            )

        except Exception as e:
            error_payload: SocketErrorPayload = pilot._error("ACTION", str(e), data.get("requestType"))
            self._emit(sid, ERROR_SEND, error_payload)
            logger.log_error(pilot_id=sid, context="ACTION", error=str(e))
            self.metrics.record_error()

    ## == ACTIVITY REQUEST
    def on_activity_request(self, data=None):
        sid = request.sid

        try:
            logger.log_event(
                pilot_id=sid,
                event_type="ACTIVITY",
                message="Pilot requested activity logs",
            )

            logs = logger.get_logs_for_pilot(sid)
            print(logs[:20])

            self._emit(sid, ACTIVITY_INFO_SEND, logs)

        except Exception as e:
            logger.log_error(pilot_id=sid, context="ACTIVITY", error=str(e))
            self._emit(sid, ACTIVITY_INFO_SEND, [])

    ## ATC EVENTS
    ## === SEND RESPONSE
    def on_atc_response(self, payload: dict):
        sid = request.sid
        start_ts = get_current_timestamp()

        if not self.atc_manager.exists(sid):
            self._emit(sid, ERROR_SEND, {"message": "ATC not connected"})
            logger.log_error(pilot_id=sid, context="ATC_RESPONSE", error="ATC not connected")
            self.metrics.record_error()
            return

        try:
            atc = self.atc_manager.get(sid)
        except KeyError as e:
            self._emit(sid, ERROR_SEND, {"message": "ATC not connected"})
            logger.log_error(pilot_id=sid, context="ATC_RESPONSE", error=str(e))
            self.metrics.record_error()
            return

        try:
            pilot_sid = payload.get("pilot_sid")
            if not pilot_sid:
                self._emit(sid, ERROR_SEND, {"message": f"Unknown pilot: {pilot_sid}"})
                logger.log_error(pilot_id=sid, context="ATC_RESPONSE", error="Missing pilot_sid")
                return

            if not self.pilots.exists(pilot_sid):
                self._emit(sid, ERROR_SEND, {"message": f"Pilot with SID {pilot_sid} does not exist"})
                logger.log_error(pilot_id=sid, context="ATC_RESPONSE", error=f"Pilot not found: {pilot_sid}")
                self.metrics.record_error()
                return

            pilot = self.pilots.get(pilot_sid)
            update: UpdateStepData = atc.handle_response(payload, pilot)

            pilot.handle_step_update(update, self.socket)

            pilot_event_payload = {
                "step_code": update.step_code,
                "status": update.status.value,
                "message": update.message,
                "timestamp": update.validated_at,
                "time_left": update.time_left,
                "label": update.label,
            }

            direction = payload.get("direction")
            if direction:
                pilot_event_payload["direction"] = str(direction).upper()

            self._emit(update.pilot_sid, ATC_RESPONSE_TO_PILOT, pilot_event_payload)

            if update.status == StepStatus.NEW:
                update.status = StepStatus.RESPONDED

            self._emit(ATC_ROOM, NEW_REQUEST_SEND, update.to_atc_payload())

            if update.step_code in CLEARANCE_CODES:
                clearance = None
                if pilot.clearances["route_change"]["instruction"]:
                    clearance = pilot.clearances["route_change"]
                elif pilot.clearances["taxi"]["instruction"]:
                    clearance = pilot.clearances["taxi"]
                elif pilot.clearances["expected"]["instruction"]:
                    clearance = pilot.clearances["expected"]

                if clearance:
                    self._emit(pilot_sid, PROPOSED_CLEARANCE_SEND, {
                        "kind": clearance["kind"],
                        "instruction": clearance["instruction"],
                    })

            if payload.get("action") in [CANCEL, UNABLE] and update.step_code in CLEARANCE_CODES:
                clearance = pilot.clear_clearance(update.step_code)

                self._emit(pilot_sid, PROPOSED_CLEARANCE_SEND, {
                    "kind": clearance["kind"],
                    "instruction": clearance["instruction"],
                })

                self._emit(ATC_ROOM, PROPOSED_CLEARANCE_SEND, {
                    "pilot_sid": pilot.sid,
                    "clearance": clearance,
                })

            logger.log_request(
                pilot_id=update.pilot_sid,
                request_type=update.step_code,
                status=update.status.value,
                message=update.message,
                time_left=update.time_left,
            )

            self.metrics.record_event(
                "atc",
                start_ts,
                get_current_timestamp(),
                payload.get("client_sent_ts"),
            )

        except ValueError as e:
            self._emit(sid, ERROR_SEND, {"message": str(e)})
            logger.log_error(pilot_id=sid, context="ATC_RESPONSE", error=str(e))
            self.metrics.record_error()

    ## === PILOT LIST
    def handle_pilot_list(self, data=None):
        sid = request.sid
        pilot_list_data = self.get_adjusted_pilot_list()
        self._emit(sid, PILOT_LIST_SEND, pilot_list_data)

    def get_adjusted_pilot_list(self) -> list[PilotPublicView]:
        pilot_list: list[Pilot] = self.pilots.get_all_pilots()
        pilot_list_data = [pilot.to_public() for pilot in pilot_list]

        for pilot_data in pilot_list_data:
            pilot = self.pilots.get(pilot_data["sid"])
            for code, step_payload in pilot_data["steps"].items():
                direction = step_payload.get("direction")
                message = interpolate_request_message(code, pilot, direction)
                step_payload["message"] = message

                status = step_payload["status"]
                if status == StepStatus.NEW.value:
                    step_payload["status"] = StepStatus.RESPONDED.value
                elif status == StepStatus.REQUESTED.value:
                    step_payload["status"] = StepStatus.NEW.value

        return pilot_list_data

    ## === MAP REQUEST
    def handle_map_request(self):
        sid = request.sid
        if not self.airport_map_manager:
            self._emit(sid, ERROR_SEND, {"message": "Airport map manager not initialized"})
            logger.log_error(pilot_id=sid, context="MAP_REQUEST", error="Airport map manager not initialized")
            self.metrics.record_error()
            return

        map_data = self.airport_map_manager.get_map()
        if not map_data:
            self._emit(sid, ERROR_SEND, {"message": "No airport map data available"})
            logger.log_error(pilot_id=sid, context="MAP_REQUEST", error="No airport map data available")
            self.metrics.record_error()
            return

        self._emit(sid, AIRPORT_MAP_DATA_SEND, map_data)

    ## === SEND CLEARANCE
    def on_clearance_request(self, payload: dict):
        sid = request.sid
        atc = self.atc_manager.get(sid)
        if not atc:
            self._emit(sid, ERROR_SEND, {"message": "ATC not connected"})
            logger.log_error(pilot_id=sid, context="CLEARANCE", error="ATC not connected")
            self.metrics.record_error()
            return

        pilot_sid = payload.get("pilot_sid")
        if not pilot_sid:
            self._emit(sid, ERROR_SEND, {"message": "Missing pilot SID"})
            logger.log_error(pilot_id=sid, context="CLEARANCE", error="Missing pilot SID")
            self.metrics.record_error()
            return

        pilot = self.pilots.get(pilot_sid)
        if not pilot:
            self._emit(sid, ERROR_SEND, {"message": f"Pilot with SID {pilot_sid} does not exist"})
            logger.log_error(pilot_id=sid, context="CLEARANCE", error=f"Pilot not found: {pilot_sid}")
            self.metrics.record_error()
            return

        try:
            kind: ClearanceType = payload.get("kind") or "expected"

            atc.validate_clearance_request(pilot, kind)
            issued_at = get_formatted_time(get_current_timestamp())
            instruction, coords = self.clearance_engine.generate_clearance(pilot)

            clearance: Clearance = Clearance(
                kind=kind,
                instruction=instruction,
                coords=coords,
                issued_at=issued_at,
            )

            pilot.set_clearance(clearance)

            self._emit(ATC_ROOM, PROPOSED_CLEARANCE_SEND, {
                "pilot_sid": pilot.sid,
                "clearance": clearance,
            })

        except Exception as e:
            self._emit(sid, ERROR_SEND, {"message": str(e)})
            logger.log_error(pilot_id=sid, context="CLEARANCE", error=str(e))
            self.metrics.record_error()

    def on_clearance_cancel(self, pilot_sid: str):
        sid = request.sid
        atc = self.atc_manager.get(sid)
        if not atc:
            self._emit(sid, ERROR_SEND, {"message": "ATC not connected"})
            logger.log_error(pilot_id=sid, context="CLEARANCE", error="ATC not connected")
            self.metrics.record_error()
            return

        if not pilot_sid:
            self._emit(sid, ERROR_SEND, {"message": "Missing pilot SID"})
            logger.log_error(pilot_id=sid, context="CLEARANCE", error="Missing pilot SID")
            self.metrics.record_error()
            return

        pilot = self.pilots.get(pilot_sid)
        if not pilot:
            self._emit(sid, ERROR_SEND, {"message": f"Pilot with SID {pilot_sid} does not exist"})
            logger.log_error(pilot_id=sid, context="CLEARANCE", error=f"Pilot not found: {pilot_sid}")
            self.metrics.record_error()
            return

        try:
            pilot.init_clearances()

            self._emit(ATC_ROOM, CLEARANCE_CANCELLED, {
                "pilot_sid": pilot.sid,
                "clearances": pilot.clearances,
            })

        except Exception as e:
            self._emit(sid, ERROR_SEND, {"message": str(e)})
            logger.log_error(pilot_id=sid, context="CLEARANCE", error=str(e))
            self.metrics.record_error()