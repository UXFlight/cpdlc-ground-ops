export const SOCKET_EMITS = {
    SEND_REQUEST: "sendRequest",
    CANCEL_REQUEST: "cancelRequest",
    SEND_ACTION: "sendAction",
    GET_STATE: "getState",
};

export const SOCKET_LISTENS = {
    CONNECT: "connect",
    DISCONNECT: "disconnect",
    CONNECTED_TO_ATC: "connectedToAtc",
    DISCONNECTED_FROM_ATC: "disconnectedFromATC",
    CLEARANCE_UPDATE: "proposed_clearance",
    TICK: "tick",
    TIMEOUT: "atcTimeout",
    ATC_RESPONSE: "atcResponse",
    ACTION_ACK: "actionAcknowledged",
    REQUEST_ACK: "requestAcknowledged",
    CANCEL_ACK: "requestCancelled",
    ERROR: "error",
}