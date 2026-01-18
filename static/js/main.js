// all events imported
import { sendRequestEvent } from './events/sendRequest.js';
import { cancelRequestEvent } from './events/cancelRequest.js';
import { toggleOverlay, touchStartEvent, handleGlobalClick, touchFeedbackButtons, closeSettings } from './events/overlay.js';
import { selectPushbackDirection } from './events/pushbackDirection.js';
import { setupSocketListeners } from './socket/socket-listens.js';
import { settingEvent } from './events/settings.js';
import { updateDashboardPanel } from './state/settingsState.js';
import { toggleSwitchEvent, setConfig } from './state/configState.js';
import { closeSettingsButton } from './events/settings.js';
import { downloadReport } from './events/downloadStats.js';
import { initVoice } from './text-to-speech.js/speech.js';
import { CLASS_NAMES, SELECTORS } from './consts/cssConsts.js';

document.addEventListener("DOMContentLoaded", () => {
  setConfig();
  updateDashboardPanel()
  setupSocketListeners() // ok
  listenToButtonEvents(); // ok
  listenToGlobalClickEvents(); // ok
  listenToHeaderEvents();
  initVoice();
});

function listenToGlobalClickEvents() {
  const overlays = document.querySelectorAll(SELECTORS.OVERLAY);

  overlays.forEach(overlay => {
    overlay.addEventListener("click", () => toggleOverlay(overlay));
  });

  document.addEventListener("click", handleGlobalClick);
  document.addEventListener("touchstart", (e) => {
    touchStartEvent(e);         // overlays
    touchFeedbackButtons(e);    // req/cancel btns
  });

  document.addEventListener("keydown", (event) => closeSettings(event));
}

function listenToButtonEvents() {
  const requestButtons = document.querySelectorAll(SELECTORS.REQUEST_BUTTONS);
  const cancelButtons = document.querySelectorAll(SELECTORS.CANCEL_BUTTONS);

  const leftButton = document.querySelector(SELECTORS.PUSHBACK_LEFT);
  const rightButton = document.querySelector(SELECTORS.PUSHBACK_RIGHT);

  const settingsIcon = document.querySelector(SELECTORS.SETTINGS_ICON);

  const downloadBtn = document.querySelector(SELECTORS.DOWNLOAD_BUTTON);

  const toggleButtons = document.querySelectorAll(SELECTORS.TOGGLE_SWITCHES);

  const closeSettings = document.querySelector(SELECTORS.CLOSE_SETTINGS_BUTTON);

  // request buttons
  requestButtons.forEach(btn => {
    btn.addEventListener("click", function (e) {
      sendRequestEvent.call(this, e);
    });
  });

  // cancel buttons
  cancelButtons.forEach(btn => {
    btn.addEventListener("click", function (e) {
      cancelRequestEvent.call(this, e);
    });
  });

  // left/ right pushback event
  leftButton.addEventListener("click", (e) => selectPushbackDirection(e));
  rightButton.addEventListener("click", (e) => selectPushbackDirection(e));

  // settings icon event
  settingsIcon.addEventListener("click", (e) => settingEvent(e));

  // download btn event
  downloadBtn.addEventListener("click", (e) => downloadReport())

  // toggle switch event
  toggleButtons.forEach(btn => {
    btn.addEventListener("click", (e) => toggleSwitchEvent(e));
  });
  
  closeSettings.addEventListener('click', () => closeSettingsButton());
}

export function listenToHeaderEvents() {
  const connectionStatus = document.querySelector(SELECTORS.CONNECTION_STATUS);
  connectionStatus.addEventListener('click', () => connectionStatus.classList.toggle(CLASS_NAMES.SHOW_TOOLTIP));
}
