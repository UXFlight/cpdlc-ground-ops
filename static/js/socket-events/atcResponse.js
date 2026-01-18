import { updateStep } from "../state/state.js";
import { displayHistoryLogs } from "../events/filter.js";
import { playNotificationSound } from "../ui/ui.js";
import { getBool, CONFIG_KEYS } from "../state/configState.js";
import { MSG_STATUS } from "../consts/status.js";
import { REQUEST_TYPE } from "../consts/flightConsts.js";
import { autoLoadAction } from "../events/action.js";
import { closeOverlay } from "../events/overlay.js";
import { speak } from "../text-to-speech.js/speech.js";
import { enableButtonsByStatus } from "../ui/buttons-ui.js";

export const handleAtcResponse = (data) => {
    const {
        step_code,
        status,
        message,
        timestamp,
        time_left,
    } = data

    const cancelBtn = document.querySelector(`.cancel-button[data-requesttype="${step_code}"]`);
    if (cancelBtn) cancelBtn.disabled = true;

    closeOverlay(step_code);

    updateStep(step_code, status, message, timestamp, time_left);

    if (checkAutoLoad(step_code, status)) setTimeout(() => autoLoadAction(step_code), 200);
    if (getBool(CONFIG_KEYS.AUDIO)) speak(message);
    else playNotificationSound();

    enableButtonsByStatus(status, step_code);

    displayHistoryLogs();
}

function checkAutoLoad(step_code, status) {
    const isLoadable = [REQUEST_TYPE.EXPECTED_TAXI_CLEARANCE, REQUEST_TYPE.TAXI_CLEARANCE].includes(step_code);
    return status === MSG_STATUS.NEW && isLoadable && getBool(CONFIG_KEYS.ACK);
}