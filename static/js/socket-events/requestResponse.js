import { state, updateStep } from "../state/state.js";
import { MSG_STATUS } from '../consts/status.js';
import { displayHistoryLogs } from "../events/filter.js";
import { SELECTORS } from "../consts/cssConsts.js";

export const handleRequestAck = (data) => {
    const { step_code, status, message, timestamp, label } = data;
    const cancelBtn = document.querySelector(SELECTORS.CANCEL_BUTTON_BY_REQUESTTYPE(step_code));
    updateStep(step_code, status, message, timestamp, null, label);
    if (cancelBtn) cancelBtn.disabled = false;
    if (state.steps[step_code].status === MSG_STATUS.CANCELLED) return;
    displayHistoryLogs();
}
