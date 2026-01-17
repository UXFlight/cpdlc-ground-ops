from app.utils.types import StepStatus

INGESCAPE_OUTPUTS = {
    "load",
    "execute", 
    "cancel",
}

REQUEST_OUTPUTS = [
    "DM_136",
    "DM_134",
    "DM_131",
    "DM_135",
    "DM_127",
    "DM_20",
    "able_intersection_departure",
    "ready_for_clearance",
    "departure_clearance",
    "startup_cancellation",
    "affirm", "negative", "roger",
    "we_can_accept", "we_cannot_accept",
    "de_icing_complete", "no_de_icing_required"
]

ACTION_OUTPUTS = [
    "load", 
    "wilco",    
    "execute", 
    "cancel", 
    "standby", 
    "unable"
]

ALL_OUTPUTS = REQUEST_OUTPUTS + ACTION_OUTPUTS


ACTION_DEFINITIONS = {
    "execute": {
        "status": StepStatus.EXECUTED.value,
        "requiredType": True,
        "allowedTypes": ["DM_135"]
    },
    "load": {
        "status": StepStatus.LOADED.value,
        "requiredType": True,
        "allowedTypes": ["DM_135", "DM_136"]
    },
    "cancel": {
        "status": StepStatus.CANCEL.value,
        "message": lambda _: 'Clearance Cancelled',
        "requiredType": False,
        "fixedType": "DM_135"
    },
    "wilco": {
        "status": StepStatus.CLOSED.value,
        "requiredType": True,
        "allowedTypes": REQUEST_OUTPUTS
    },
    "standby": {
        "status": StepStatus.STANDBY.value,
        "requiredType": True,
        "allowedTypes": REQUEST_OUTPUTS
    },
    "unable": {
        "status": StepStatus.UNABLE.value,
        "requiredType": True,
        "allowedTypes": REQUEST_OUTPUTS
    }
}

TIMER_DURATION = 90

DEFAULT_PILOT_REQUESTS = {
    "DM_136": "REQUEST EXPECTED TAXI ROUTING [pos]",
    "DM_134": "REQUEST STARTUP",
    "DM_131": "REQUEST PUSHBACK [dir]",
    "DM_135": "REQUEST TAXI [pos]",
    "DM_127": "REQUEST DE-ICING [pos]",
    "DM_20": "CONTACT GROUND ON FOR FURTHER INSTRUCTIONS."
}

DEFAULT_STEPS = [
    {"label": "Expected Taxi Clearance", "requestType": "DM_136"},
    {"label": "Engine Startup", "requestType": "DM_134"},
    {"label": "Pushback", "requestType": "DM_131"},
    {"label": "Taxi Clearance", "requestType": "DM_135"},
    {"label": "De-Icing", "requestType": "DM_127"},
]
