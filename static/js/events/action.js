import { updateStep } from '../state/state.js';
import { MSG_STATUS } from '../consts/status.js';
import { getActionInfoFromEvent } from '../utils/utils.js';
import { emitAction } from '../socket/socket-emits.js';

export const actionEvent = async (e) => {
  e.stopPropagation();
  const { action, requestType } = getActionInfoFromEvent(e);
  if (!action || !requestType) return;

  try {
    emitAction(action, requestType);
  } catch (err) {
    console.error(`Error handling action '${action}':`, err);
    updateStep(requestType, MSG_STATUS.ERROR, err.message, requestType);
  }
};

export function autoLoadAction(requestType) {
  try {
    emitAction(MSG_STATUS.LOAD, requestType);
  } catch (err) {
    console.error(`Error handling action '${action}':`, err);
    updateStep(requestType, MSG_STATUS.ERROR, err.message, requestType);
  }
}