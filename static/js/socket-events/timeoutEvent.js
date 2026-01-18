import { displayHistoryLogs } from "../events/filter.js";
import { state, updateStep } from "../state/state.js";
import { updateTimerVisual } from "../ui/timer-ui.js";
import { getBool, CONFIG_KEYS } from "../state/configState.js";
import { autoSendRequest } from "../events/sendRequest.js";
import { enableRequestButton } from "../ui/buttons-ui.js";
import { MSG_STATUS } from "../consts/status.js";


export const tickUpdate = (data) => {
    const { 
        step_code,
        timeLeft 
    } = data
    
    const step = state.steps[step_code];
    if (!step) return;

    const total = step.status === MSG_STATUS.STANDBY ? 300 : 90;
    step.timeLeft = timeLeft;

    updateTimerVisual(step_code, timeLeft, total); 
};

export const timeoutEvent = (data) => {
    const { 
            step_code,
            status,
            message,
            timestamp,
            timeLeft
        } = data;

    updateStep(step_code, status, message, timestamp, timeLeft);
    displayHistoryLogs();
    enableRequestButton(step_code)

    if (getBool(CONFIG_KEYS.RETRY)) autoSendRequest(step_code);
}