import { dashboardNeedsRefresh, updateDashboardPanel } from '../state/settingsState.js';
import { state } from '../state/state.js';
import { MSG_STATUS } from '../consts/status.js';
import { closeCurrentOverlay } from '../utils/utils.js';
import { CLASS_NAMES, SELECTORS } from '../consts/cssConsts.js';

// overlay event
export const toggleOverlay = (overlay) => {
  document.querySelectorAll(SELECTORS.OVERLAY_OPEN).forEach(open => {
    open.classList.remove(CLASS_NAMES.OPEN);
  });

  const action = overlay.dataset.requesttype;
  if (!action || state.steps[action].status === MSG_STATUS.CLOSED) return;

  overlay.classList.add(CLASS_NAMES.OPEN);
};

export const closeOverlay = (requestType) => {
  const requestOverlay = document.querySelector(SELECTORS.OVERLAY_BY_REQUESTTYPE_CAMEL(requestType));
  if (requestOverlay) requestOverlay.classList.remove(CLASS_NAMES.OPEN);
}

export const handleGlobalClick = (event) => {
  const settingPanel = document.querySelector(SELECTORS.SETTINGS_PANEL);
  const settingsIcon = document.querySelector(SELECTORS.SETTINGS_ICON);

  const isInsideOverlay = event.target.closest(SELECTORS.OVERLAY);
  const isInsideConnection = event.target.closest(SELECTORS.CONNECTION_STATUS);
  if (!isInsideConnection) {
    document.querySelector(SELECTORS.CONNECTION_STATUS)?.classList.remove(CLASS_NAMES.SHOW_TOOLTIP);
  }
  if (!isInsideOverlay) closeCurrentOverlay();

  const clickedOutsideSettings =
    settingPanel.classList.contains(CLASS_NAMES.ACTIVE) &&
    !settingPanel.contains(event.target) &&
    !settingsIcon.contains(event.target);

  if (clickedOutsideSettings) {
    settingPanel.classList.remove(CLASS_NAMES.ACTIVE);
  }
};

// FOR MOBILE DEVICES
export const touchStartEvent = (e) => {
    const el = e.target.closest(SELECTORS.OVERLAY);
    if (!el) return;
    el.classList.add(CLASS_NAMES.TOUCHED);
    setTimeout(() => { el.classList.remove(CLASS_NAMES.TOUCHED) }, 150);
}

export const touchFeedbackButtons = (e) => {
  const btn = e.target.closest(SELECTORS.REQUEST_OR_CANCEL_BUTTONS);
  if (!btn || btn.disabled) return;

  btn.classList.add(CLASS_NAMES.TOUCHED);

  setTimeout(() => {
    btn.classList.remove(CLASS_NAMES.TOUCHED);
  }, 120);
};

// KEYDOWN
export const closeSettings = (event) => {
  const settingPanel = document.querySelector(SELECTORS.SETTINGS_PANEL);
  if (!settingPanel) return;
  const isVisible = settingPanel.classList.contains(CLASS_NAMES.ACTIVE);

  if ((event.key === "Escape" || event.key === "Tab") && isVisible) {
    event.preventDefault();
    settingPanel.classList.remove(CLASS_NAMES.ACTIVE);
  } else if (event.key === "Tab" && !isVisible) {
    event.preventDefault();
    settingPanel.classList.add(CLASS_NAMES.ACTIVE);
    if (dashboardNeedsRefresh()) updateDashboardPanel();
  }
};
