import { state, updateDirection } from '../state/state.js';
import { MSG_STATUS } from '../consts/status.js';
import { isConnected } from '../utils/utils.js';
import { REQUEST_TYPE } from '../consts/flightConsts.js';
import { togglePushbackState } from '../ui/buttons-ui.js';
import { CLASS_NAMES, SELECTORS } from '../consts/cssConsts.js';

// pushback direction
export const selectPushbackDirection = (e) => {
  const direction = e.target.textContent;
  const prevDirection = state.steps[REQUEST_TYPE.PUSHBACK].direction;
  const pushbackStatus = state.steps[REQUEST_TYPE.PUSHBACK].status;
  const isActive = [MSG_STATUS.NEW , MSG_STATUS.LOADED, MSG_STATUS.EXECUTED, MSG_STATUS.CLOSED].includes(pushbackStatus);
  if (isActive) document.querySelector(SELECTORS.PUSHBACK_DIRECTION_ID(direction)).disabled = true;
  if (!direction || direction === prevDirection || isActive) return;

  togglePushbackState(false, direction)
  updateDirection(direction);
};

export const enablePushbackRequest = () => {
  const right = document.querySelector(SELECTORS.PUSHBACK_RIGHT);
  const left = document.querySelector(SELECTORS.PUSHBACK_LEFT);
  
  if (right.classList.contains(CLASS_NAMES.ACTIVE) || left.classList.contains(CLASS_NAMES.ACTIVE)) {
    const pushbackBtn = document.querySelector(SELECTORS.PUSHBACK_BUTTON);
    if (pushbackBtn) pushbackBtn.disabled = false;
  }
}
