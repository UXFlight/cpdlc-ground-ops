import { updateStep, state } from '../state/state.js';
import { MSG_STATUS } from '../consts/status.js';
import { getRequestTypeFromEvent } from "../utils/utils.js";
import { emitCancelRequest } from "../socket/socket-emits.js";
import { REQUEST_TYPE } from '../consts/flightConsts.js';
import { togglePushbackState } from '../ui/buttons-ui.js';

export async function cancelRequestEvent(e) {
  e.stopPropagation();
  const requestType = getRequestTypeFromEvent(e);
  if (!requestType) return;

                      
  if (requestType === REQUEST_TYPE.PUSHBACK) {
    togglePushbackState(true)
    console.log(state.steps[REQUEST_TYPE.PUSHBACK].status)
    console.log(MSG_STATUS.REQUESTED)
    if (state.steps[REQUEST_TYPE.PUSHBACK].status !== MSG_STATUS.REQUESTED) return
  }

  try {
    emitCancelRequest(requestType);
    this.disabled = true;
  } catch (err) {
    console.error("Cancel error:", err);
    updateStep(requestType, MSG_STATUS.ERROR, "Network error during cancellation");
  }
}