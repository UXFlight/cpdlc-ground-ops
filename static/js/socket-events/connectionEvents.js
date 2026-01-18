import { enablePushbackRequest } from "../events/pushbackDirection.js";
import { CLASS_NAMES, SELECTORS } from "../consts/cssConsts.js";
import { CONNECTION_STATUS } from "../consts/connectionConsts.js";

const indicator = document.querySelector(SELECTORS.CONNECTION_INDICATOR);
const text = document.querySelector(SELECTORS.CONNECTION_TEXT);


export function renderConnectionState(connection) {
    updateMainIndicator(connection);
    updateTooltip(connection);
  }
  
function updateMainIndicator(connection) {
    indicator.className = "status-indicator";
    const { backend, atc } = connection;

    if (backend === CONNECTION_STATUS.CONNECTED && atc.status === CONNECTION_STATUS.CONNECTED) {
        indicator.classList.add(CLASS_NAMES.CONNECTED);
        text.textContent = `connected to ${atc.facility}`;
        enablePushbackRequest();
    } else if (backend === CONNECTION_STATUS.CONNECTED && atc.status !== CONNECTION_STATUS.CONNECTED) {
        indicator.classList.add(CLASS_NAMES.PARTIAL);
        text.textContent = "establishing connection to ATC...";
    } else if (backend === CONNECTION_STATUS.DISCONNECTED) {
        indicator.classList.add(CLASS_NAMES.DISCONNECTED);
        text.textContent = "disconnected from server";
    } else {
        indicator.classList.add(CLASS_NAMES.CONNECTING);
        text.textContent = "Connecting to server...";
    }
}

function updateTooltip(connection) {
    const backendText = document.querySelector(SELECTORS.BACKEND_TEXT);
    const backendIcon = document.querySelector(SELECTORS.BACKEND_ICON);
    const atcText = document.querySelector(SELECTORS.ATC_TEXT);
    const atcIcon = document.querySelector(SELECTORS.ATC_ICON);
    const timestampEl = document.querySelector(SELECTORS.CONNECTION_TIMESTAMP);

    if (!backendText || !backendIcon || !atcText || !atcIcon || !timestampEl) return;

    backendText.textContent =
        connection.backend === CONNECTION_STATUS.CONNECTED
            ? "Connected"
            : connection.backend === CONNECTION_STATUS.DISCONNECTED
            ? "Disconnected"
            : "Connecting...";

    atcText.textContent =
        connection.atc.status === CONNECTION_STATUS.CONNECTED
            ? `Connected to ${connection.atc.facility}`
            : connection.atc.status === CONNECTION_STATUS.DISCONNECTED
            ? "Disconnected"
            : "Waiting...";

    backendIcon.className = "status-dot " + (
        connection.backend === CONNECTION_STATUS.CONNECTED
            ? "success"
            : connection.backend === CONNECTION_STATUS.DISCONNECTED
            ? "failure"
            : "pending"
    );

    atcIcon.className = "status-dot " + (
        connection.atc.status === CONNECTION_STATUS.CONNECTED
            ? "success"
            : connection.atc.status === CONNECTION_STATUS.DISCONNECTED
            ? "failure"
            : "pending"
    );

    if (connection.backend === CONNECTION_STATUS.CONNECTED) {
        const now = new Date();
        const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        timestampEl.textContent = timeStr;
    }
}
