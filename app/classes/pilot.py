from typing import Optional, Dict
import uuid

from app.classes.step import Step
from app.managers.log_manager import logger
from app.utils.color import set_pilot_color
from app.utils.constants import ACTION_DEFINITIONS, DEFAULT_STEPS
from app.utils.parse import step_code_to_clearance_type
from app.utils.time_utils import get_current_timestamp, get_formatted_time
from app.managers import TimerManager
from app.classes.socket import SocketService
from app.utils.types import Clearance, ClearanceType, LocationInfo, Plane, SocketError, StepStatus, UpdateStepData, PilotPublicView

DEFAULT_LOCATION: LocationInfo = {
    "coord": (0.0, 0.0),
    "type": "parking",
    "name": "UNKNOWN"
}

DEFAULT_PLANE: Plane = {
    "spawn_pos": DEFAULT_LOCATION,
    "current_pos": DEFAULT_LOCATION,
    "final_pos": DEFAULT_LOCATION,
    "current_heading": 0.0,
    "current_speed": 0.0
}

class Pilot:
    def __init__(self, sid: str, plane: Plane = DEFAULT_PLANE):
        self.sid = sid
        self.steps: Dict[str, Step] = {}
        self.color : str = set_pilot_color(sid)
        self.history: list[UpdateStepData] = []
        self.timer_manager = TimerManager(self.sid)
        
        self.plane: Plane = plane
        
        self.clearances = self.init_clearances()
        self.current_clearance : ClearanceType = "expected"
        self.initialize_steps()

    def initialize_steps(self):
        for step_info in DEFAULT_STEPS:
            code = step_info["requestType"]
            label = step_info["label"]
            request_id = str(uuid.uuid4())
            self.steps[code] = Step(step_code=code, label=label, request_id=request_id)
            
    def init_clearances(self) -> Dict[ClearanceType, Clearance]:
        return {
            "expected": {
                "kind": "expected",
                "instruction": "",
                "coords": [],
                "issued_at": "",
                
            },
            "taxi": {
                "kind": "taxi",
                "instruction": "",
                "coords": [],
                "issued_at": "",
            },
            "route_change": {
                "kind": "route_change",
                "instruction": "",
                "coords": [],
                "issued_at": "" ,
            }
            
        }
        
    def set_clearance(self, clearance: Clearance):
        if clearance["kind"] not in self.clearances:
            raise ValueError(f"Unknown clearance type: {clearance['kind']}")
        
        self.clearances[clearance["kind"]] = clearance
        self.current_clearance = clearance["kind"]

    def get_step(self, step_code: str) -> Optional[Step]:
        return self.steps.get(step_code)

    ## === Handle ATC Step Update ===
    def handle_step_update(self, update: UpdateStepData, socket: SocketService | None = None) -> dict:
        step = self.get_step(update.step_code)
        if not step:
            step = Step.from_update(update)
            self.steps[update.step_code] = step

        step.apply_update(update)
        self.history.append(update)

        if update.time_left and socket:
            self.start_timer_for_step(step, socket)

        return step.to_dict()

    ## === Handle Send Request ===
    def handle_send_request(self, data: dict) -> UpdateStepData:
        request_type = data.get("requestType")
        if not request_type:
            raise ValueError("Missing requestType")

        step = self.get_step(request_type)
        if not step:
            raise ValueError(f"Unknown step: {request_type}")
        
        if step.step_code == "DM_131":
            if not data.get("direction"):
                raise ValueError("Pushback direction is required for DM_131")
            step.label = f"Pushback {data['direction'].upper()}"

        if step.status in {
            StepStatus.REQUESTED,
            StepStatus.NEW,
            StepStatus.LOADED,
            StepStatus.EXECUTED,
        }:
            raise ValueError(f"{request_type} already in progress")

        update = UpdateStepData(
            pilot_sid=self.sid,
            step_code=request_type,
            status=StepStatus.REQUESTED,
            message="Request sent to ATC",
            validated_at=get_current_timestamp(),
            request_id=step.request_id,
            time_left=None,
            label=step.label
        )

        step.apply_update(update)
        self.history.append(update)

        logger.log_request(
            pilot_id=self.sid,
            request_type=request_type,
            status=update.status.value,
            message=update.message,
            time_left=update.time_left
        )

        return update

    ## === Handle Cancel Request ===
    def handle_cancel_request(self, data: dict) -> UpdateStepData:
        print(f"[CANCEL] {self.sid} - {data}")
        request_type = data.get("requestType")
        if not request_type:
            raise ValueError("Missing requestType")

        step = self.get_step(request_type)
        if not step:
            raise ValueError(f"Unknown step: {request_type}")

        if step.status != StepStatus.REQUESTED:
            raise ValueError(f"Cannot cancel step in status {step.status.value}")

        update = UpdateStepData(
            pilot_sid=self.sid,
            step_code=request_type,
            status=StepStatus.CANCELLED,
            message="Request cancelled by pilot",
            validated_at=get_current_timestamp(),
            request_id=step.request_id,
            time_left=step.time_left,
            label=step.label
        )

        step.apply_update(update)
        self.history.append(update)

        logger.log_request(
            pilot_id=self.sid,
            request_type=request_type,
            status=update.status.value,
            message=update.message,
            time_left=update.time_left
        )

        return update

    
    def clear_clearance(self, step_code: str) -> Clearance:
        kind = step_code_to_clearance_type(step_code)
        if not kind:
            raise ValueError(f"Unknown step_code: {step_code}")
        
        empty_clearance : Clearance = {
            "kind": kind,
            "instruction": "",
            "coords": [],
            "issued_at": get_formatted_time(get_current_timestamp()),
        }

        self.clearances[kind] = empty_clearance
        return empty_clearance
    
    ## === Handle Actions ===
    def process_action(self, data: dict) -> UpdateStepData:
        action = data.get("action")
        request_type = data.get("requestType")

        if not request_type:
            raise ValueError(f"Missing requestType for action")
        if not action:
            raise ValueError(f"Missing action for {request_type}")

        config = ACTION_DEFINITIONS.get(action)
        if not config:
            raise ValueError(f"Unknown action: {action} for {request_type}")

        if config.get("requiredType") and request_type not in config.get("allowedTypes", []):
            raise ValueError(f"Invalid requestType for action '{action}'", request_type)

        final_type = config.get("fixedType", request_type)
        step = self.get_step(final_type)
        if not step:
            raise ValueError(f"Unknown step: {final_type}")

        valid_transitions = {
            "new": {"load", "wilco", "standby", "unable"},
            "loaded": {"execute", "cancel"} if request_type == "DM_135" else {"wilco", "standby", "unable"},
            "executed": {"wilco", "standby", "unable"},
            "standby": {"wilco", "standby", "unable"},
            "standby": {"wilco", "standby", "unable"},
        }

        allowed = valid_transitions.get(step.status.value, set())
        if action not in allowed:
            raise ValueError(f"Action '{action}' not allowed for step '{final_type}' in status '{step.status.value}'")

        if action in {"wilco", "cancel", "unable"}:
            self.timer_manager.stop_timer(final_type)
            time_left = None
        elif action == "standby":
            time_left = 300
        else:
            time_left = step.time_left

        status_str = config["status"]
        status_enum = StepStatus(status_str)

        update = UpdateStepData(
            pilot_sid=self.sid,
            step_code=final_type,
            label=step.label,
            status=status_enum,
            message=step.message or '',
            validated_at=get_current_timestamp(),
            request_id=step.request_id,
            time_left=time_left
        )

        step.apply_update(update)
        self.history.append(update)

        logger.log_action(
            pilot_id=self.sid,
            action_type=action,
            status=update.status.value,
            message=update.message,
            time_left=update.time_left
        )

        return update

    ## === Error formatting ===
    def _error(self, context: str, message: str, request_type: Optional[str] = None,
               status: str = "error", time_left: Optional[float] = None) -> SocketError:
        logger.log_error(
            pilot_id=self.sid,
            context=f"{context}:{self.sid}",
            error=message,
            time_left=time_left
        )

        return {
            "event": "error",
            "payload": {
                "requestType": request_type,
                "status": status,
                "message": message,
                "timestamp": get_current_timestamp()
            }
        }

    ## === Timer ===
    def start_timer_for_step(self, step: Step, socket: SocketService):
        logger.log_event(self.sid, 'TICK', f"{step.step_code} {step.time_left}s left")
        self.timer_manager.start_timer(
            step=step,
            step_code=step.step_code,
            on_tick=lambda step_code, step: self.handle_tick(step_code, step, socket),
            on_timeout=lambda step_code, step: self.handle_timeout(step_code, step, socket)
        )

    def handle_tick(self, step_code: str, step: Step, socket: SocketService):
        socket.send("tick", {
            "step_code": step_code,
            "timeLeft": step.time_left
        }, room=self.sid)

    def handle_timeout(self, step_code: str, step: Step, socket: SocketService):
        if step.status.value in {"wilco", "cancelled", "unable", "executed", "closed"}:
            logger.log_event(self.sid, "TIMEOUT_SKIP", f"Ignored timeout for {step_code} - already {step.status}")
            return
        
        update = UpdateStepData(
            pilot_sid=self.sid,
            step_code=step_code,
            label=step.label,
            status=StepStatus.TIMEOUT,
            message="ATC request timed out.",
            validated_at=get_current_timestamp(),
            request_id=step.request_id,
            time_left=step.time_left
        )

        update = step.apply_update(update)

        socket.send("atcTimeout", {
            "step_code": step_code,
            "status": update.status.value,
            "message": update.message,
            "timestamp": update.validated_at,
            "timeLeft": update.time_left,
        }, room=self.sid)
        
        socket.send("new_request", update.to_atc_payload(), room="atc_room")

        # gss_client.send_update_step(update.to_dict()) #keeping track of gss
        logger.log_event(self.sid, "TIMEOUT", f"{step_code} expired.")

    ## === Cleanup ===
    def cleanup(self):
        try:
            logger.log_event(self.sid, "SYSTEM", "Cleaning up pilot session.")
            self.timer_manager.stop_all()
            self.steps.clear()
            self.history.clear()
            self.expected_clearance = None
            self.active_clearance = None
            self.previous_clearance = None
            self.color = set_pilot_color(self.sid)  # Reset color for next session
            logger.log_event(self.sid, "SYSTEM", "Pilot cleanup complete.")
        except Exception as e:
            logger.log_error(self.sid, "CLEANUP", f"Cleanup failed: {e}")
            
    ## === Public View ===
    def get_plane_data(self) -> Plane:
        return self.plane


    # format helpers
    def to_public(self) -> PilotPublicView:
        return {
            "sid": self.sid,
            "color": self.color,
            "steps": {code: step.to_step_public_view() for code, step in self.steps.items()},
            "history": [update.to_step_event() for update in self.history],
            "plane": self.plane,
            "clearances": self.clearances,
            "current_clearance": self.current_clearance
        }