import { state, updateDirection } from '../state/state.js';
import { MSG_STATUS } from '../consts/status.js';
import { isConnected } from '../utils/utils.js';
import { REQUEST_TYPE } from '../consts/flightConsts.js';
import { togglePushbackState } from '../ui/buttons-ui.js';

// pushback direction
export const selectPushbackDirection = (e) => {
  const direction = e.target.textContent;
  const prevDirection = state.steps[REQUEST_TYPE.PUSHBACK].direction;
  const pushbackStatus = state.steps[REQUEST_TYPE.PUSHBACK].status;
  const isActive = [MSG_STATUS.NEW , MSG_STATUS.LOADED, MSG_STATUS.EXECUTED, MSG_STATUS.CLOSED].includes(pushbackStatus);
  if (isActive) document.getElementById(`pushback-${direction}`).disabled = true;
  if (!direction || direction === prevDirection || isActive) return;

  togglePushbackState(false, direction)
  updateDirection(direction);
};

export const enablePushbackRequest = () => {
  const right = document.getElementById('pushback-right');
  const left = document.getElementById('pushback-left');
  
  if (right.classList.contains('active') || left.classList.contains('active')) {
    const pushbackBtn = document.getElementById("pushback-btn");
    if (pushbackBtn) pushbackBtn.disabled = false;
  }
}