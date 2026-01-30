from flask import request  # type: ignore
from typing import TYPE_CHECKING, Optional
from app.utils.constants import TIMER_DURATION
from app.utils.parse import interpolate_request_message, parse_status, parse_status_from_str
from app.utils.time_utils import get_current_timestamp, get_formatted_time
from app.utils.types import Clearance, ClearanceType, ConnectInfo, PilotPublicView, SocketError, StepStatus, UpdateStepData
from app.managers.log_manager import logger
from app.classes.clearance import ClearanceEngine

if TYPE_CHECKING:
    from app.classes.pilot import Pilot
    from app.classes.socket import SocketService
    from app.managers.pilot_manager import PilotManager
    from app.managers.atc_manager import AtcManager
    from app.managers.airport_map_manager import AirportMapManager

class SocketManager:
    def __init__(self, socket_service: "SocketService", pilot_manager: "PilotManager",
                 atc_manager: "AtcManager", airport_map_manager : "AirportMapManager",
                 metrics_store=None):
        self.socket: "SocketService" = socket_service
        self.pilots: "PilotManager" = pilot_manager
        self.atc_manager: "AtcManager" = atc_manager
        self.airport_map_manager : "AirportMapManager" = airport_map_manager
        self.clearance_engine = ClearanceEngine(airport_map_manager.map_data)
        self.metrics = metrics_store
        self._disconnecting: set[str] = set()
        
        # not injected
        self.logger = logger
        self.connection_info: ConnectInfo = {
            "facility": "KLAX",
            "connectedSince": get_current_timestamp()
        }

    def _emit_event(self, sid: str, result: dict | SocketError):
        if not result or not isinstance(result, dict):
            self.logger.log_error(pilot_id=sid, context="SOCKET", error="Invalid result payload")
            return
        self.socket.send(result["event"], result["payload"], room=sid)

    def _record_event(self, role: str, start_ts: float, client_sent_ts: Optional[float]) -> None:
        if self.metrics:
            self.metrics.record_event(role, start_ts, get_current_timestamp(), client_sent_ts)

    def _record_error(self) -> None:
        if self.metrics:
            self.metrics.record_error()

    def init_events(self):
        self.socket.listen("connect", self.on_connect)
        self.socket.listen("disconnect", self.on_disconnect)

        # PILOT EVENTS
        self.socket.listen("sendRequest", self.on_send_request)
        self.socket.listen("cancelRequest", self.on_cancel_request)
        self.socket.listen("sendAction", self.on_action_event)
        
        # ATC EVENTS
        self.socket.listen("getPilotList", self.handle_pilot_list)
        self.socket.listen("selectPilot", self.handle_atc_select_pilot)
        self.socket.listen("getAirportMapData", self.handle_map_request)
        self.socket.listen("getClearance", self.on_clearance_request)

        # GSS EVENTS
        # gss_client.listen("gss_connected", self.on_gss_connect)
        # gss_client.listen("step_updated", self.on_receive_step_update)
        self.socket.listen("atcResponse", self.on_atc_response)

    ## PILOT UIS EVENTS
    ## === CONNECT
    def on_connect(self, auth=None):
        sid = request.sid # type: ignore
        role = auth.get("r") if auth else None  # 0 = pilot, 1 = atc

        if role == 0:
            public_view : PilotPublicView = self.pilots.create(sid)
            logger.log_event(pilot_id=sid, event_type="SOCKET", message=f"Pilot connected: {sid}")
            self.socket.send("connectedToAtc", self.connection_info, room=sid)
            if self.atc_manager.has_any():
                self.socket.send("pilot_connected", public_view, room="atc_room")

        elif role == 1:
            self.atc_manager.create(sid)
            self.socket.enter_room(sid, room="atc_room")
            logger.log_event(pilot_id=sid, event_type="SOCKET", message=f"ATC connected: {sid}")
            
            pilot_list_data = self.get_adjusted_pilot_list()
            self.socket.send("pilot_list", pilot_list_data, room=sid)

            atc_list = self.atc_manager.get_all()
            self.socket.send("atc_list", atc_list, room="atc_room")

        else:
            logger.log_event(pilot_id=sid, event_type="SOCKET", message="Unknown role -- disconnecting")
            self.socket.disconnect(sid)

    def on_disconnect(self, data=None):
        sid = request.sid # type: ignore
        if sid in self._disconnecting:
            return
        self._disconnecting.add(sid)

        try:
            if self.pilots.exists(sid):
                self.pilots.remove(sid)
                logger.log_event(pilot_id=sid, event_type="SOCKET", message=f"Pilot disconnected: {sid}")

                if self.atc_manager.has_any():
                    try:
                        self.socket.send("pilot_disconnected", sid, room="atc_room")
                    except Exception as e:
                        logger.log_error(pilot_id=sid, context="DISCONNECT", error=str(e))

            elif self.atc_manager.exists(sid):
                self.atc_manager.remove(sid)
                self.socket.leave_room(sid, room="atc_room")
                atc_list = self.atc_manager.get_all()
                try:
                    self.socket.send("atc_list", atc_list, room="atc_room", skip_sid=sid)
                except Exception as e:
                    logger.log_error(pilot_id=sid, context="DISCONNECT", error=str(e))
                logger.log_event(pilot_id=sid, event_type="SOCKET", message=f"ATC disconnected: {sid}")

            else:
                logger.log_event(pilot_id=sid, event_type="SOCKET", message="Unknown SID disconnected")
        finally:
            self._disconnecting.discard(sid)


    ## === SEND REQUESTS
    def on_send_request(self, data: dict):
        sid = request.sid # type: ignore
        pilot : Pilot = self.pilots.get(sid)
        start_ts = get_current_timestamp()

        try:
            step_payload: UpdateStepData = pilot.handle_send_request(data)
            step_code = step_payload.step_code
            # gss_client.send_update_step(step_payload.to_dict())
            self._emit_event(sid, {
                "event": "requestAcknowledged",
                "payload": step_payload.to_ack_payload()
            })
            
            message = interpolate_request_message(step_code, pilot, data.get("direction"))
            step_payload.message = message
            
            status = parse_status(step_payload.status)
            step_payload.status = status
            
            if step_code in ["DM_135", "DM_136"]:
                kind: ClearanceType = "expected" if step_code == "DM_136" else "taxi"
                issued_at = get_formatted_time(get_current_timestamp())
                instruction, coords = self.clearance_engine.generate_clearance(pilot)

                clearance: Clearance = {
                    "kind": kind,
                    "instruction": instruction,
                    "coords": coords,
                    "issued_at": issued_at,
                }
                
                pilot.set_clearance(clearance)

                self._emit_event("atc_room", {
                    "event": "proposed_clearance",
                    "payload": {
                        "pilot_sid": pilot.sid,
                        "clearance": clearance
                    }
                })
                     
            self._emit_event("atc_room", {
                "event": "new_request",
                "payload": step_payload.to_atc_payload()
            })
            self._record_event("pilot", start_ts, data.get("client_sent_ts"))

        except Exception as e:
            error_payload: SocketError = pilot._error("REQUEST", str(e), data.get("requestType"))
            self._emit_event(sid, error_payload)
            logger.log_error(pilot_id=sid, context="REQUEST", error=str(e))
            self._record_error()
            

    ## === CANCEL REQUEST
    def on_cancel_request(self, data: dict):
        sid = request.sid # type: ignore
        pilot = self.pilots.get(sid)
        start_ts = get_current_timestamp()

        try:
            update_data: UpdateStepData = pilot.handle_cancel_request(data)

            self._emit_event(sid, {
                "event": "requestCancelled",
                "payload": update_data.to_ack_payload()
            })
            
            self._emit_event("atc_room", { # i could create new channel, but event 'new_request' is alr working!
                "event": "new_request",
                "payload": update_data.to_atc_payload()
            })
            
            if update_data.step_code in ["DM_135", "DM_136"]:
                clearance = pilot.clear_clearance(update_data.step_code)
                self._emit_event("atc_room", {
                    "event": "proposed_clearance",
                    "payload": {
                        "pilot_sid": pilot.sid,
                        "clearance": clearance
                    }
                })
                
                self._emit_event(pilot.sid, {
                    "event": "proposed_clearance",
                    "payload": {
                        "kind": clearance["kind"],
                        "instruction": clearance["instruction"]
                    }
                })
            self._record_event("pilot", start_ts, data.get("client_sent_ts"))
            
        except Exception as e:
            error_payload: SocketError = pilot._error("CANCEL", str(e), data.get("requestType"))
            self._emit_event(sid, error_payload)
            logger.log_error(pilot_id=sid, context="CANCEL", error=str(e))
            self._record_error()

    ## === ACTION EVENTS
    def on_action_event(self, data: dict):
        sid = request.sid # type: ignore
        pilot = self.pilots.get(sid)
        start_ts = get_current_timestamp()

        try:
            update_data : UpdateStepData = pilot.process_action(data)
            self._emit_event(sid, {
                "event": "actionAcknowledged",
                "payload": update_data.to_ack_payload()
            })
            
            self._emit_event("atc_room", {
                "event": "new_request",
                "payload": update_data.to_atc_payload()
            })
            
            if data.get("action") in ['cancel', 'unable'] and update_data.step_code in ["DM_135", "DM_136"]:
                clearance = pilot.clear_clearance(update_data.step_code)
                
                self._emit_event(sid, {
                    "event": "proposed_clearance",
                    "payload": {
                        "kind": clearance["kind"],
                        "instruction": clearance["instruction"]
                    }
                })
                
                self._emit_event("atc_room", {
                    "event": "proposed_clearance",
                    "payload": {
                        "pilot_sid": pilot.sid,
                        "clearance": clearance
                    }
                })
            self._record_event("pilot", start_ts, data.get("client_sent_ts"))

        except Exception as e:
            error_payload = pilot._error("ACTION", str(e), data.get("requestType"))
            self._emit_event(sid, error_payload)
            logger.log_error(pilot_id=sid, context="ACTION", error=str(e))
            self._record_error()

    ## ATC EVENTS
    ## === SEND RESPONSE
    def on_atc_response(self, payload: dict):
        sid = request.sid  # type: ignore
        start_ts = get_current_timestamp()

        if not self.atc_manager.exists(sid):
            self.socket.send("error", {"message": "ATC not connected"}, room=sid)
            logger.log_error(pilot_id=sid, context="ATC_RESPONSE", error="ATC not connected")
            self._record_error()
            return
        try:
            atc = self.atc_manager.get(sid)
        except KeyError as e:
            self.socket.send("error", {"message": "ATC not connected"}, room=sid)
            logger.log_error(pilot_id=sid, context="ATC_RESPONSE", error=str(e))
            self._record_error()
            return

        try:
            pilot_sid = payload.get("pilot_sid")
            if not pilot_sid:
                self.socket.send("error", {"message": f"Unknown pilot: {pilot_sid}"}, room=sid)
                logger.log_error(pilot_id=sid, context="ATC_RESPONSE", error="Missing pilot_sid")
                return

            if not self.pilots.exists(pilot_sid):
                self.socket.send("error", {"message": f"Pilot with SID {pilot_sid} does not exist"}, room=sid)
                logger.log_error(pilot_id=sid, context="ATC_RESPONSE", error=f"Pilot not found: {pilot_sid}")
                self._record_error()
                return
            pilot = self.pilots.get(pilot_sid)

            update: UpdateStepData = atc.handle_response(payload, pilot)

            pilot.handle_step_update(update, self.socket)

            self.socket.send("atcResponse", {
                "step_code": update.step_code,
                "status": update.status.value,
                "message": update.message,
                "timestamp": update.validated_at,
                "time_left": update.time_left,
            }, room=update.pilot_sid)
            
            if update.status == StepStatus.NEW:
                update.status = StepStatus.RESPONDED

            self._emit_event("atc_room", {
                "event": "new_request",
                "payload": update.to_atc_payload()
            })
            if update.step_code in ["DM_135", "DM_136"]:
                if pilot.clearances["route_change"]["instruction"]:
                    clearance = pilot.clearances["route_change"]
                elif pilot.clearances["taxi"]["instruction"]:
                    clearance = pilot.clearances["taxi"]
                elif pilot.clearances["expected"]["instruction"]:
                    clearance = pilot.clearances["expected"]
                if clearance: 
                    self._emit_event(pilot_sid, {
                        "event": "proposed_clearance",
                        "payload": {
                            "kind": clearance["kind"],
                            "instruction": clearance["instruction"]
                        }
                    })
                
            if payload.get("action") in ['cancel', 'unable'] and update.step_code in ["DM_135", "DM_136"]:
                clearance = pilot.clear_clearance(update.step_code)
                
                self._emit_event(pilot_sid, {
                    "event": "proposed_clearance",
                    "payload": {
                        "kind": clearance["kind"],
                        "instruction": clearance["instruction"]
                    }
                })
                
                print("Emitting proposed clearance to ATC room")
                
                self._emit_event("atc_room", {
                    "event": "proposed_clearance",
                    "payload": {
                        "pilot_sid": pilot.sid,
                        "clearance": clearance
                    }
                })

            logger.log_request(
                pilot_id=update.pilot_sid,
                request_type=update.step_code,
                status=update.status.value,
                message=update.message,
                time_left=update.time_left
            )
            self._record_event("atc", start_ts, payload.get("client_sent_ts"))

        except ValueError as e:
            self.socket.send("error", {"message": str(e)}, room=sid)
            logger.log_error(pilot_id=sid, context="ATC_RESPONSE", error=str(e))
            self._record_error()
        
    ## === PILOT LIST
    def handle_pilot_list(self, data=None):
        sid = request.sid  # type: ignore
        pilot_list_data = self.get_adjusted_pilot_list()
        self.socket.send("pilot_list", pilot_list_data, room=sid)
        
    def get_adjusted_pilot_list(self) -> list[PilotPublicView]:
        pilot_list: list[Pilot] = self.pilots.get_all_pilots()
        pilot_list_data = [pilot.to_public() for pilot in pilot_list]

        for pilot_data in pilot_list_data:
            pilot = self.pilots.get(pilot_data["sid"])
            for code, step_payload in pilot_data["steps"].items():
                direction = step_payload.get("direction")
                message = interpolate_request_message(code, pilot, direction)  # type: ignore
                step_payload["message"] = message

                status = step_payload["status"]
                if status == StepStatus.NEW.value:
                    step_payload["status"] = StepStatus.RESPONDED.value
                elif status == StepStatus.REQUESTED.value:
                    step_payload["status"] = StepStatus.NEW.value

        return pilot_list_data

    ## === SELECT PILOT
    def handle_atc_select_pilot(self, pilot_sid: str):
        sid = request.sid # type: ignore
        if not pilot_sid:
            self.socket.send("error", {"message": "Missing pilot SID"}, room=sid)
            logger.log_error(pilot_id=sid, context="SELECT_PILOT", error="Missing pilot SID")
            self._record_error()
            return

        if not self.pilots.exists(pilot_sid):
            self.socket.send("error", {"message": f"Pilot with SID {pilot_sid} does not exist"}, room=sid)
            logger.log_error(pilot_id=sid, context="SELECT_PILOT", error=f"Pilot not found: {pilot_sid}")
            self._record_error()
            return
        
        atc = self.atc_manager.get(sid)
        if not atc:
            self.socket.send("error", {"message": "ATC not connected"}, room=sid)
            logger.log_error(pilot_id=sid, context="SELECT_PILOT", error="ATC not connected")
            self._record_error()
            return
        
        atc.selected_pilot = pilot_sid
        self.socket.send("selected_pilot", atc.to_public(), room="atc_room")

    ## === MAP REQUEST
    def handle_map_request(self):
        sid = request.sid # type: ignore
        if not self.airport_map_manager:
            self.socket.send("error", {"message": "Airport map manager not initialized"}, room=sid)
            logger.log_error(pilot_id=sid, context="MAP_REQUEST", error="Airport map manager not initialized")
            self._record_error()
            return

        map_data = self.airport_map_manager.get_map()
        if not map_data:
            self.socket.send("error", {"message": "No airport map data available"}, room=sid)
            logger.log_error(pilot_id=sid, context="MAP_REQUEST", error="No airport map data available")
            self._record_error()
            return

        self.socket.send("airport_map_data", map_data, room=sid)
        
    ## === SEND CLEARANCE
    def on_clearance_request(self, payload: dict):
        sid = request.sid  # type: ignore
        atc = self.atc_manager.get(sid)
        if not atc:
            self.socket.send("error", {"message": "ATC not connected"}, room=sid)
            logger.log_error(pilot_id=sid, context="CLEARANCE", error="ATC not connected")
            self._record_error()
            return

        pilot_sid = payload.get("pilot_sid")
        if not pilot_sid:
            self.socket.send("error", {"message": "Missing pilot SID"}, room=sid)
            logger.log_error(pilot_id=sid, context="CLEARANCE", error="Missing pilot SID")
            self._record_error()
            return

        pilot = self.pilots.get(pilot_sid)
        if not pilot:
            self.socket.send("error", {"message": f"Pilot with SID {pilot_sid} does not exist"}, room=sid)
            logger.log_error(pilot_id=sid, context="CLEARANCE", error=f"Pilot not found: {pilot_sid}")
            self._record_error()
            return

        try:
            kind: ClearanceType = payload.get("kind") or "expected"

            atc.validate_clearance_request(pilot, kind)
            issued_at = get_formatted_time(get_current_timestamp())
            instruction, coords = self.clearance_engine.generate_clearance(pilot)

            clearance: Clearance = {
                "kind": kind,
                "instruction": instruction,
                "coords": coords,
                "issued_at": issued_at,
            }

            pilot.set_clearance(clearance)
            self._emit_event("atc_room", {
                "event": "proposed_clearance",
                "payload": {
                    "pilot_sid": pilot.sid,
                    "clearance": clearance
                }
            })

        except Exception as e:
            self.socket.send("error", {"message": str(e)}, room=sid)
            logger.log_error(pilot_id=sid, context="CLEARANCE", error=str(e))
            self._record_error()
