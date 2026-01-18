import { updateStep } from "../state/state.js";
import { MSG_STATUS } from '../consts/status.js';
import { closeCurrentOverlay } from "../utils/utils.js";
import { displayHistoryLogs } from "../events/filter.js";
import { enableButtonsByStatus } from "../ui/buttons-ui.js";
import { updateTaxiClearanceMsg } from "../ui/ui.js";
import { REQUEST_TYPE } from "../consts/flightConsts.js";

export function handleActionResponse(data) {
    const { step_code, status, message, validated_at, time_left } = data;
    updateStep(step_code, status, message, validated_at, time_left);
    displayHistoryLogs();
    enableButtonsByStatus(status, step_code);
    closeCurrentOverlay();
}