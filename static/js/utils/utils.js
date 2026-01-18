import { state } from '../state/state.js';
import { MSG_STATUS } from '../consts/status.js';
import { REQUEST_TYPE } from '../consts/flightConsts.js';

// small utils functions
export function invalidRequest(action) {
  return (!action || blockSecondRequest(action) || action === REQUEST_TYPE.PUSHBACK && !state.steps[action].direction)
}

function blockSecondRequest(action) {
  const currentStatus = state.steps[action]?.status;
  return currentStatus === MSG_STATUS.CLOSED || currentStatus === MSG_STATUS.NEW || currentStatus === MSG_STATUS.LOADED;
}

export function closeCurrentOverlay() {
    const open = document.querySelector(".overlay.open");
    if (open) open.classList.remove("open");
}

export function getLatestEntry(stepKey) {
  const group = state.history.find(h => h.stepKey === stepKey);
  return group?.entries[group.entries.length - 1] ?? null;
}

export function getRequestTypeFromEvent(e) {
  const target = e.target;
  if (target.dataset && target.dataset.requesttype) return target.dataset.requesttype;
  const parentWithAction = target.closest("[data-action]");
  if (parentWithAction) return parentWithAction.dataset.action;
  return null;
}

export function getActionInfoFromEvent(e) {
  const target = e.target.closest("button");
  if (!target) return null;
  const idParts = target.id.split("-");
  if (idParts.length !== 2) return null;
  const action = target.dataset.actionType; // action type
  const requestType = idParts[1];           // request type
  return { action, requestType };
}

export function isConnected() {
  return state.connection.backend === "connected" && state.connection.atc.status === "connected";
}