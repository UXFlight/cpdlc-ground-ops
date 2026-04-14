from dataclasses import dataclass
from enum import Enum
from typing import List, Literal, Optional, Tuple, TypedDict, Union

# POSSIBLE STATUS
class StepStatus(Enum):
    IDLE = "idle"
    REQUESTED = "requested"
    RESPONDED = "responded"
    NEW = "new"
    LOADED = "loaded"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    CLOSED = "closed"
    STANDBY = "standby"
    UNABLE = "unable"
    CANCEL = "cancel"
    TIMEOUT = "timeout"

ACTIVE_TAXI_STEP_STATUSES = {
    StepStatus.STANDBY,
    StepStatus.REQUESTED,
    StepStatus.RESPONDED,
    StepStatus.NEW,
    StepStatus.LOADED,
    StepStatus.EXECUTED,
    StepStatus.CLOSED
}

# POSSIBLE REQUESTS CODES
class StepCode(Enum):
    EXPECTED_TAXI_CLEARANCE = "DM_136"
    ENGINE_STARTUP = "DM_134"
    PUSHBACK = "DM_131"
    TAXI_CLEARANCE = "DM_135"
    DE_ICING = "DM_127"
    VOICE_CONTACT = "DM_20"

# ===============================

# PAYLOAD TO UPDATE STEP
class StepUpdatePayload(TypedDict):
    pilot_sid: str
    step_code: str
    label: str
    status: str
    message: str
    validated_at: float
    request_id: str
    time_left: Optional[float]


class AckUpdatePayload(TypedDict):
    pilot_sid: str
    step_code: str
    status: str
    message: str
    validated_at: float
    time_left: Optional[float]
    label: str
# ===============================

@dataclass
class UpdateStepData:
    pilot_sid: str
    step_code: str #! change this to enum soon
    label: str
    status: StepStatus
    message: str
    validated_at: float
    request_id: str
    time_left: Optional[float] = None

    def to_ack_payload(self) -> AckUpdatePayload:
        return {
            "pilot_sid": self.pilot_sid,
            "step_code": self.step_code,
            "status": self.status.value,
            "message": self.message,
            "validated_at": self.validated_at,
            "time_left": self.time_left,
            "label": self.label
        }
        
    def to_atc_payload(self) -> StepUpdatePayload:
        return {
            "pilot_sid": self.pilot_sid,
            "step_code": self.step_code,
            "label": self.label,
            "status": self.status.value,
            "message": self.message,
            "validated_at": self.validated_at,
            "request_id": self.request_id,
            "time_left": self.time_left
        }
        
    def to_step_event(self) -> "StepEvent":
        return StepEvent(
            step_code=self.step_code,
            status=self.status.value,
            timestamp=self.validated_at,
            message=self.message,
            request_id=self.request_id
        )

    @staticmethod
    def from_dict(data: dict) -> Optional["UpdateStepData"]:
        try:
            return UpdateStepData(
                pilot_sid=data["pilot_sid"],
                step_code=data["step_code"],
                label=data.get("label", data["step_code"]),
                status=StepStatus(data["status"]),
                message=data["message"],
                validated_at=data["validated_at"],
                request_id=data["request_id"],
                time_left=data.get("time_left"),
            )
        except KeyError as e:
            print(f"[PARSE] Missing key in update_step: {e}")
            return None

# ERROR PAYLOAD =================
class SocketErrorPayload(TypedDict):
    requestType: Optional[str]
    status: str
    message: str
    timestamp: float

class SocketError(TypedDict):
    event: str
    payload: SocketErrorPayload

# ===============================

# ACKNOWLEDGEMENT PAYLOAD =======
class SocketRequestAckPayload(TypedDict):
    event: str
    payload: StepUpdatePayload

# ===============================

# PILOT CONNECTION INFO =========
class ConnectInfo(TypedDict):
    facility: str
    connectedSince: str | float
# ===============================

class PilotConnectInfo(ConnectInfo):
    pilotSid: str

## SIMPLIFIED 'PUBLICVIEW' DATA FOR ATC FRONTEND
LonLat = Tuple[float, float]

# === Airport Info ===
class AirportInfo(TypedDict):
    icao: str
    name: str
    elevation: float

# === Runway ===
class Runway(TypedDict):
    name: str
    start: LonLat
    end: LonLat
    width: float
    surface: int

# === Helipad ===
class Helipad(TypedDict):
    name: str
    location: LonLat
    heading: float
    length: float
    width: float


# === Taxiway ===
TaxiwayWidth = Literal["A", "B", "C", "D", "E", "F"]

# === Parking ===
ParkingType = Literal["gate", "tie_down", "hangar", "ramp", "unknown"]

class Taxiway(TypedDict):
    name: str
    start: LonLat
    end: LonLat
    width: Union[str, TaxiwayWidth]
    is_runway: bool
    one_way: bool


class ParkingPosition(TypedDict):
    name: str
    location: LonLat
    heading: float
    type: ParkingType


# === Complete Map Data ===
class AirportMapData(TypedDict):
    airport_info: AirportInfo
    runways: List[Runway]
    helipads: List[Helipad]
    taxiways: List[Taxiway]
    parking: List[ParkingPosition]

# === Plane ===
class LocationInfo(TypedDict):
    name: str
    type: Literal["parking", "taxiway", "runway"]
    coord: LonLat

class Plane(TypedDict):
    spawn_pos: LocationInfo
    current_pos: LocationInfo
    final_pos: LocationInfo
    current_heading: float
    current_speed: float
    
# === Clearance ===
ClearanceType = Literal["expected", "taxi", "route_change"]
class Clearance(TypedDict):
    kind: ClearanceType
    instruction: str
    coords: List[LocationInfo]
    issued_at: str
    
# === Step Public View ===
class StepPublicView(TypedDict):
    step_code: str
    label: str
    status: str
    message: str
    validated_at: float
    time_left: Optional[float]
    request_id: str
    
    
# SIMPLIFIED STEP FOR PILOT HISTORY
class StepEvent(TypedDict):
    step_code: str
    status: str
    timestamp: float
    message: str
    request_id: str

# ===============================

# === Pilot Public View ===
class PilotPublicView(TypedDict):
    sid: str
    steps: dict[str, StepPublicView]
    color: str
    history: list[StepEvent]
    plane: Plane
    clearances: dict[ClearanceType, Clearance]  # <- clé = kind
    current_clearance: ClearanceType 
    
    
## ATC Public View ===
class AtcPublicView(TypedDict):
    sid: str
    selectedPilot: str  # pilot sid