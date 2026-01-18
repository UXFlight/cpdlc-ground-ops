export const ALL_ACTIONS = {
    LOAD:    { id: 'load' },
    EXECUTE: { id: 'execute' },
    CANCEL:  { id: 'cancel' },
    WILCO:   { id: 'wilco' },
    STANDBY: { id: 'standby' },
    UNABLE:  { id: 'unable' }
};

export const REQUEST_TYPE = {
    EXPECTED_TAXI_CLEARANCE: "DM_136",
    ENGINE_STARTUP: "DM_134",
    PUSHBACK: 'DM_131',
    TAXI_CLEARANCE: "DM_135",
    DE_ICING: 'DM_127',
    VOICE_CONTACT: 'DM_20',
}

export const LOADABLE_REQUEST_TYPES = ["DM_136", "DM_135"];
