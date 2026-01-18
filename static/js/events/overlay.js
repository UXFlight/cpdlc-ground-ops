import { dashboardNeedsRefresh, updateDashboardPanel } from '../state/settingsState.js';
import { state } from '../state/state.js';
import { MSG_STATUS } from '../consts/status.js';
import { closeCurrentOverlay } from '../utils/utils.js';

// overlay event
export const toggleOverlay = (overlay) => {
  document.querySelectorAll(".overlay.open").forEach(open => {
    open.classList.remove("open");
  });

  const action = overlay.dataset.requesttype;
  if (!action || state.steps[action].status === MSG_STATUS.CLOSED) return;

  overlay.classList.add("open");
};

export const closeOverlay = (requestType) => {
  const requestOverlay = document.querySelector(`.overlay[data-requestType="${requestType}"]`)
  if (requestOverlay) requestOverlay.classList.remove('open');
}

export const handleGlobalClick = (event) => {
  const settingPanel = document.getElementById("settings-panel");
  const settingsIcon = document.getElementById("settings-icon");

  const isInsideOverlay = event.target.closest(".overlay");
  const isInsideConnection = event.target.closest("#connection-status");
  if (!isInsideConnection) {
    document.getElementById("connection-status")?.classList.remove("show-tooltip");
  }
  if (!isInsideOverlay) closeCurrentOverlay();

  const clickedOutsideSettings =
    settingPanel.classList.contains("active") &&
    !settingPanel.contains(event.target) &&
    !settingsIcon.contains(event.target);

  if (clickedOutsideSettings) {
    settingPanel.classList.remove("active");
  }
};

// FOR MOBILE DEVICES
export const touchStartEvent = (e) => {
    const el = e.target.closest(".overlay");
    if (!el) return;
    el.classList.add("touched");
    setTimeout(() => { el.classList.remove("touched") }, 150);
}

export const touchFeedbackButtons = (e) => {
  const btn = e.target.closest('.request-button, .cancel-button');
  if (!btn || btn.disabled) return;

  btn.classList.add('touched');

  setTimeout(() => {
    btn.classList.remove('touched');
  }, 120);
};

// KEYDOWN
export const closeSettings = (event) => {
  const settingPanel = document.getElementById("settings-panel");
  if (!settingPanel) return;
  const isVisible = settingPanel.classList.contains("active");

  if ((event.key === "Escape" || event.key === "Tab") && isVisible) {
    event.preventDefault();
    settingPanel.classList.remove("active");
  } else if (event.key === "Tab" && !isVisible) {
    event.preventDefault();
    settingPanel.classList.add("active");
    if (dashboardNeedsRefresh()) updateDashboardPanel();
  }
};

