import { showSpinner, showTick } from "../ui/ui.js";
import { closeCurrentOverlay, getRequestTypeFromEvent, invalidRequest } from "../utils/utils.js";
import { updateStep } from '../state/state.js';
import { MSG_STATUS } from '../consts/status.js';
import { emitRequest } from '../socket/socket-emits.js';
import { getRequestPayload } from "../utils/requestPayload.js";
import { SELECTORS } from "../consts/cssConsts.js";

export async function sendRequestEvent(e) {
  e.preventDefault();
  e.stopPropagation();
  this.disabled = true;

  const requestType = getRequestTypeFromEvent(e);
  if (!requestType || invalidRequest(requestType)) return;
  showSpinner(requestType);
  try {
    const payload = getRequestPayload(requestType);
    emitRequest(requestType, payload);
  } catch (err) {
    showTick(requestType, true);
    closeCurrentOverlay();
    updateStep(requestType, MSG_STATUS.ERROR, err.message || "Network error");
    console.error("Network error:", err);
  }
};

export const autoSendRequest = (requestType) => {
  const requestButton = document.querySelector(SELECTORS.REQUEST_BUTTON_ID(requestType));
  if (requestButton) requestButton.disabled = true;
  showSpinner(requestType);
  try {
    const payload = getRequestPayload(requestType);
    emitRequest(requestType, payload);
  } catch (err) {
    showTick(requestType, true);
    closeCurrentOverlay();
    updateStep(requestType, MSG_STATUS.ERROR, err.message || "Network error");
    console.error("Network error:", err);
  }
}