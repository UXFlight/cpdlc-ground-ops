export const WORKFLOW_BUTTONS = {
    DM_136: {
        new: ['LOAD'],
        loaded: ['WILCO', 'STANDBY', 'UNABLE'],
        standby: ['WILCO', 'UNABLE']
    },
    DM_135: {
        new: ['LOAD'],
        loaded: ['EXECUTE', 'CANCEL'],
        executed: ['WILCO', 'STANDBY', 'UNABLE'],
        standby: ['WILCO', 'UNABLE'],
        cancel: ['LOAD']
    },
    default: {
        NEW: ['WILCO', 'STANDBY', 'UNABLE'],
        STANDBY: ['WILCO', 'UNABLE']
    }
};