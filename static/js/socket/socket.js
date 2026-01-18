import { SERVER_URL } from "../consts/serverUrl.js";

const ROLE_PILOT = 0;

const socket = io(SERVER_URL, { //! single connection for each pilot
  auth: { r: ROLE_PILOT }
}); 

function send(event, data) {
  socket.emit(event, data);
}

function listen(event, callback) {
  socket.on(event, callback);
}

export { send, listen, socket };
