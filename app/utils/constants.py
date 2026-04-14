from app.utils.types import StepStatus

EXPECTED_TAXI_CLEARANCE = "DM_136"
ENGINE_STARTUP = "DM_134"
PUSHBACK = 'DM_131'
TAXI_CLEARANCE = "DM_135"
DE_ICING = 'DM_127'
VOICE_CONTACT = 'DM_20'

LOAD = "load"
WILCO = "wilco"
EXECUTE = "execute"
CANCEL = "cancel"
STANDBY = "standby"
UNABLE = "unable"
AFFIRM = "affirm"

DEFAULT_TIMER_DURATION = 90
STANDBY_TIMER_DURATION = 300

DEFAULT_STEPS = [ # used on frontend!
    {"label": "Expected Taxi Clearance", "requestType": EXPECTED_TAXI_CLEARANCE},
    {"label": "Engine Startup", "requestType": ENGINE_STARTUP},
    {"label": "Pushback", "requestType": PUSHBACK},
    {"label": "Taxi Clearance", "requestType": TAXI_CLEARANCE},
    {"label": "De-Icing", "requestType": DE_ICING},
]

REQUEST_OUTPUTS = [
    EXPECTED_TAXI_CLEARANCE,
    ENGINE_STARTUP,
    PUSHBACK,
    TAXI_CLEARANCE,
    DE_ICING,
    VOICE_CONTACT,
]

ACTION_OUTPUTS = [ # ingescape integration. not used rn
    LOAD, 
    WILCO,    
    EXECUTE, 
    CANCEL, 
    STANDBY, 
    UNABLE
]

CLEARANCE_CODES = [EXPECTED_TAXI_CLEARANCE, TAXI_CLEARANCE]
PUSHBACK_DIRECTIONS = ['LEFT', 'RIGHT']

ACTION_WORKFLOW = {
    AFFIRM: (StepStatus.NEW, DEFAULT_TIMER_DURATION),
    STANDBY: (StepStatus.STANDBY, STANDBY_TIMER_DURATION),
    UNABLE: (StepStatus.UNABLE, None),
}

ACTION_DEFINITIONS = {
    EXECUTE: {
        "status": StepStatus.EXECUTED,
        "has_required_type": True,
        "allowed_types": [TAXI_CLEARANCE]
    },
    LOAD: {
        "status": StepStatus.LOADED,
        "has_required_type": True,
        "allowed_types": [TAXI_CLEARANCE, EXPECTED_TAXI_CLEARANCE]
    },
    CANCEL: {
        "status": StepStatus.CANCEL,
        "has_required_type": True,
        "fixedType": TAXI_CLEARANCE,
        "allowed_types": []
    },
    WILCO: {
        "status": StepStatus.CLOSED,
        "has_required_type": True,
        "allowed_types": REQUEST_OUTPUTS
    },
    STANDBY: {
        "status": StepStatus.STANDBY,
        "has_required_type": True,
        "allowed_types": REQUEST_OUTPUTS
    },
    UNABLE: {
        "status": StepStatus.UNABLE,
        "has_required_type": True,
        "allowed_types": REQUEST_OUTPUTS
    }
}

DEFAULT_PILOT_REQUESTS = {
    TAXI_CLEARANCE: "REQUEST EXPECTED TAXI ROUTING [pos]",
    ENGINE_STARTUP: "REQUEST STARTUP",
    PUSHBACK: "REQUEST PUSHBACK [dir]",
    TAXI_CLEARANCE: "REQUEST TAXI [pos]",
    DE_ICING: "REQUEST DE-ICING [pos]",
    VOICE_CONTACT: "CONTACT GROUND ON FOR FURTHER INSTRUCTIONS."
}

def get_valid_transitions(request_type: str) -> dict[str, set[str]]:
    loaded_actions = (
        {EXECUTE, CANCEL}
        if request_type == TAXI_CLEARANCE
        else {WILCO, STANDBY, UNABLE}
    )
    return {
        StepStatus.NEW.value: {LOAD, WILCO, STANDBY, UNABLE},
        StepStatus.LOADED.value: loaded_actions,
        StepStatus.EXECUTED.value: {WILCO, STANDBY, UNABLE},
        StepStatus.STANDBY.value: {WILCO, STANDBY, UNABLE},
    }
