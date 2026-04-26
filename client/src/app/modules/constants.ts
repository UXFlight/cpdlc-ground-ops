export const LABELS: Record<string, string> = {
    DM_136: 'EXPECTED TAXI CLEARANCE',
    DM_134: 'ENGINE STARTUP',
    DM_131: 'PUSHBACK',
    DM_135: 'TAXI CLEARANCE',
    DM_127: 'DE_ICING',
    DM_20: 'VOICE CONTACT',
};

export enum SOCKET_SENDS  {
    GET_AIRPORT_MAP_DATA = 'getAirportMapData',
    SELECT_AIRCRAFT = 'selectAircraft',
    GET_PILOT_LIST = 'getPilotList',
    GET_CLEARANCE = 'getClearance',
    CANCEL_CLEARANCE = 'cancelClearance',
    ATC_RESPONSE = 'atcResponse'
}

export enum SOCKET_LISTENS  {
    CONNECT = 'connect',
    DISCONNECT = 'disconnect',
    PILOT_LIST = 'pilot_list',
    NEW_PILOT_CONNECTED = 'pilot_connected',
    PILOT_DISCONNECTED = 'pilot_disconnected',
    NEW_REQUEST = 'new_request',
    PROPOSED_CLEARANCE = 'proposedClearance',
    CLEARANCE_CANCELLED = 'clearancesCancelled',
    ATC_LIST = 'atc_list',
    ERROR = 'error'
}