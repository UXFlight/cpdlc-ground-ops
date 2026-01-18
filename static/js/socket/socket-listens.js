import { listen } from "./socket.js";
import { handleAtcResponse } from "../socket-events/atcResponse.js";
import { renderConnectionState } from "../socket-events/connectionEvents.js";
import { tickUpdate, timeoutEvent } from "../socket-events/timeoutEvent.js";
import { state } from "../state/state.js";
import { enableAllRequestButtons, disableAllRequestButtons } from "../ui/buttons-ui.js";
import { handleActionResponse } from "../socket-events/actionResponse.js";
import { handleRequestAck } from "../socket-events/requestResponse.js";
import { handleError } from "../socket-events/errorEvent.js";
import { handleCancelRequest } from "../socket-events/cancelRequestResponse.js";
import { SOCKET_LISTENS } from "../consts/socketConsts.js";
import { setConnectionInfos } from "../state/settingsState.js";
import { updateClearance } from "../socket-events/clearanceUpdate.js";
import { CONNECTION_STATUS } from "../consts/connectionConsts.js";

export function setupSocketListeners() {
  listen(SOCKET_LISTENS.CONNECT, () => {
    state.connection.backend = CONNECTION_STATUS.CONNECTED;
    renderConnectionState(state.connection);
  });

  listen(SOCKET_LISTENS.DISCONNECT, () => {
    state.connection.backend = CONNECTION_STATUS.DISCONNECTED;
    state.connection.atc.status = CONNECTION_STATUS.DISCONNECTED;
    state.connection.atc.facility = null;
    renderConnectionState(state.connection);
    disableAllRequestButtons();
  });

  listen(SOCKET_LISTENS.CONNECTED_TO_ATC, (data) => {
    state.connection.atc.status = CONNECTION_STATUS.CONNECTED;
    state.connection.atc.facility = data.facility;
    renderConnectionState(state.connection);
    enableAllRequestButtons();
    setConnectionInfos(data.sid, data.connectedSince);
  });

  listen(SOCKET_LISTENS.DISCONNECTED_FROM_ATC, () => {
    state.connection.atc.status = CONNECTION_STATUS.DISCONNECTED;
    state.connection.atc.facility = null;
    renderConnectionState(state.connection);
  });

  listen(SOCKET_LISTENS.ATC_RESPONSE, handleAtcResponse);

  listen(SOCKET_LISTENS.REQUEST_ACK, handleRequestAck);
  listen(SOCKET_LISTENS.CANCEL_ACK, handleCancelRequest);
  listen(SOCKET_LISTENS.ACTION_ACK, handleActionResponse);
  
  //! lock in
  listen(SOCKET_LISTENS.TICK, tickUpdate);
  listen(SOCKET_LISTENS.TIMEOUT, timeoutEvent);

  // clearance update
  listen(SOCKET_LISTENS.CLEARANCE_UPDATE, updateClearance);

  // why handling errors if program is good
  listen(SOCKET_LISTENS.ERROR, handleError);
}
