from app.classes.pilot import Pilot
from app.utils.time_utils import get_current_timestamp
from app.utils.type_validation import validate_atc_payload
from app.utils.types import AtcPublicView, SocketError, StepStatus, UpdateStepData

class Atc:
    def __init__(self, atc_id: str):
        self.atc_id = atc_id
        self.selected_pilot: str = ''
    
    def to_public(self) -> AtcPublicView:
        return {
            "sid": self.atc_id,
            "selectedPilot": self.selected_pilot
        }
        
    def handle_response(self, payload: dict, pilot: Pilot) -> UpdateStepData:
        pilot_sid, step_code, action, message, request_id = validate_atc_payload(payload)
        direction = str(payload.get("direction") or "").upper()

        step = pilot.get_step(step_code)
        if not step:
            raise ValueError(f"Step {step_code} not found for pilot {pilot_sid}")

        if step.status == StepStatus.NEW:
            raise ValueError(f"Cannot respond to step {step_code} in status NEW")

        match action:
            case "affirm":
                new_status = StepStatus.NEW
                time_left = 90.0
            case "standby":
                new_status = StepStatus.STANDBY
                time_left = 300.0
            case "unable":
                new_status = StepStatus.UNABLE
                time_left = None
            case _:
                raise ValueError(f"Invalid action: {action}")

        if step_code == "DM_131" and direction in {"LEFT", "RIGHT"}:
            step.label = f"Pushback {direction}"
            if direction not in message.upper():
                message = f"{message} (Direction: {direction})"

        return UpdateStepData(
            pilot_sid=pilot_sid,
            step_code=step_code,
            label=step.label,
            status=new_status,
            message=message,
            validated_at=get_current_timestamp(),
            request_id=request_id,
            time_left=time_left
        )
        
    def validate_clearance_request(self, pilot: Pilot, kind: str):
        if not pilot.plane["spawn_pos"]:
            raise ValueError(f"Pilot {pilot.sid} has no position")

        if kind not in ["expected", "taxi"]:
            raise ValueError(f"Invalid clearance kind: {kind}")

        # if kind == "taxi" and not pilot.has_requested_pushback(): #! potentiel robustesse!
        #     raise ValueError("Cannot issue taxi clearance before pushback request")
