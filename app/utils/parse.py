from typing import TYPE_CHECKING, Optional, cast
from app.utils.constants import DEFAULT_PILOT_REQUESTS
from app.utils.types import ClearanceType, StepStatus

if TYPE_CHECKING:
    from app.classes.pilot import Pilot
    
CLEARANCE_TYPE_MAP: dict[str, ClearanceType] = {
    "DM_134": "route_change",
    "DM_135": "taxi",
    "DM_136": "expected"
}

def step_code_to_clearance_type(step_code: str) -> ClearanceType | None:
    return CLEARANCE_TYPE_MAP.get(step_code, None)

def interpolate_request_message(step_code: str, pilot: "Pilot", direction: Optional[str] = None) -> str:
    raw_msg = DEFAULT_PILOT_REQUESTS.get(step_code, "Request sent")

    from_loc = pilot.plane.get("current_pos", {})
    name = from_loc.get("name", "UNKNOWN")
    type_ = from_loc.get("type", "POS")
    location_str = f"{name} ({type_})"

    dir_str = direction.upper() if direction else "[no specified direction]"

    return (
        raw_msg
        .replace("[pos]", location_str)
        .replace("[dir]", dir_str)
    )
        
def parse_status(status: StepStatus) -> StepStatus:
    if status == StepStatus.REQUESTED:
        return StepStatus.NEW
    return status