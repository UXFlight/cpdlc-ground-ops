
import { MSG_STATUS } from '../consts/status.js';
import { getRecentClearance } from '../state/clearance.js';

// loader
export function showSpinner(requestType) {
  const spinner = document.getElementById(`${requestType}_spinner`);
  if (spinner) spinner.style.display = "inline-block";
  hideTick(requestType);
}

export function showTick(requestType, isError = false) {
  const tick = document.getElementById(`${requestType}_tick`);
  const wrapper = document.querySelector(`.overlay[data-requestType="${requestType}"]`);

  hideSpinner(requestType);
  if (wrapper) wrapper.setAttribute('data-status', isError ? 'error' : 'fulfilled');
  if (!tick) return;

  tick.style.display = "inline-block";
  tick.textContent = isError ? "✖" : "✔";
  tick.classList.toggle('error', isError);
  tick.classList.toggle('success', !isError);
}

export function hideSpinner(requestType) {
  const spinner = document.getElementById(`${requestType}_spinner`);
  if (spinner) spinner.style.display = "none";
}

export function hideTick(requestType) {
  const tick = document.getElementById(`${requestType}_tick`);
  if (tick) {
    tick.style.display = 'none';
    tick.classList.remove('error');
  }
}

export function ensureMessageBoxNotEmpty(divId='history-log-box') {
  const historyLogBox = document.getElementById(divId);
  const noMessages = document.getElementById('empty-history-message');
  if (historyLogBox.classList.contains('empty')) {
      historyLogBox.classList.remove('empty');
      noMessages?.classList.add('hidden');
  }
}

export function clearMessageBox(boxId='history-log-box') {
  ensureMessageBoxNotEmpty();
  const box = document.getElementById(boxId);
  if (box) box.innerHTML = '';
}


export function playNotificationSound() {
    const audio = new Audio('/static/mp3/notif.mp3');
    audio.volume = 0.3;
    audio.play().catch(err => console.warn('Unable to play sound:', err));
}

export function flashElement(div) {
    div.classList.add('flash');
    setTimeout(() => div.classList.remove('flash'), 1500);
}


export function updateTaxiClearanceMsg() {
  const recent = getRecentClearance();
  const box = document.querySelector(".taxi-clearance-box");
  const messageBox = document.getElementById("taxi-clearance-message");

  const oldTag = document.getElementById("expected-tag");
  if (oldTag) oldTag.remove();

  if (!recent) {
    messageBox.innerHTML = `<p class="empty-box-message">No clearance received</p>`;
    box.classList.remove("active");
    return;
  }

  const { kind, instruction } = recent;

  const tokens = instruction.split(" ").map(
    word => `<span class="taxi-token">${word}</span>`
  ).join(" ");

  messageBox.innerHTML = `<div class="clearance-grid">${tokens}</div>`;
  box.classList.add("active");

  box.classList.remove("pulse");
  void box.offsetWidth;
  box.classList.add("pulse");

  if (kind) {
    const tag = document.createElement("span");
    tag.id = "expected-tag";
    tag.className = kind;
    tag.textContent = `${kind.toUpperCase()} CLEARANCE`;
    box.prepend(tag);
  }
}

// display snackbar messages
export function updateSnackbar(requestType, status, customMessage = null, isError = true) {
  let message;

  switch (status) {
    case MSG_STATUS.CANCELLED:
      message = `${formatLabel(requestType)} request cancelled.`;
      break;
    case MSG_STATUS.ERROR:
      message = customMessage || `An error occurred on ${formatLabel(requestType)}.`;
      break;
    case "success":
      message = customMessage || "Operation successful.";
      isError = false;
      break;
    default:
      message = customMessage || formatLabel(status);
  }

  // showSnackbar(message, isError);
}

// SNACKBAR
export function showSnackbarFromPayload(payload) {
  const {
    requestType = null,
    status = "info",
    message = "An event occurred.",
    timestamp = null
  } = payload;

  const isError = status === "error" || status === "failed";

  const container = document.getElementById("snackbar-container");
  if (!container) return;

  const snackbar = document.createElement("div");
  snackbar.className = `snackbar ${isError ? "snackbar-error" : "snackbar-success"}`;

  const header = document.createElement("div");
  header.className = "snack-header";

  if (requestType) {
    const typeSpan = document.createElement("span");
    typeSpan.className = "type";
    typeSpan.textContent = requestType.replaceAll("_", " ");
    header.appendChild(typeSpan);
  }

  const statusSpan = document.createElement("span");
  statusSpan.className = "status";
  statusSpan.textContent = status.toUpperCase();
  header.appendChild(statusSpan);

  const body = document.createElement("div");
  body.className = "snack-body";

  const msg = document.createElement("div");
  msg.className = "message";
  msg.textContent = message;
  body.appendChild(msg);

  if (timestamp) {
    const time = document.createElement("div");
    time.className = "timestamp";
    time.textContent = timestamp;
    body.appendChild(time);
  }

  snackbar.appendChild(header);
  snackbar.appendChild(body);
  container.appendChild(snackbar);

  void snackbar.offsetWidth;

  snackbar.classList.add("visible");

  // setTimeout(() => {
  //   snackbar.classList.remove("visible");
  //   snackbar.classList.add("fade-out");
  // }, 4000);

  // setTimeout(() => snackbar.remove(), 4600);
}

function formatLabel(text) {
  return text
    .replace(/_/g, " ")
    .replace(/\b\w/g, char => char.toUpperCase());
}

// STATUS UPDATER //
export function updateMessageStatus(requestType, newStatus) {
  const message = document.querySelector(`.new-message[data-requesttype="${requestType}"]`);
  if (!message) return;

  const statusEl = message.querySelector('.status');
  if (!statusEl) return;

  Object.values(MSG_STATUS).forEach(status => statusEl.classList.remove(status.toLowerCase()));

  statusEl.textContent = newStatus.toUpperCase();
  statusEl.classList.add(newStatus.toLowerCase());
  message.dataset.status = newStatus.toLowerCase();
}

export function updateOverlayStatus(requestType, newStatus) {
  const overlay = document.querySelector(`.overlay[data-requesttype="${requestType}"]`);
  if (!overlay) return;

  Object.values(MSG_STATUS).forEach(status => {
      overlay.classList.remove(`status-${status.toLowerCase()}`);
      overlay.dataset.status = "";
  });

  const status = newStatus.toLowerCase();
  overlay.classList.add(`status-${status}`);
  overlay.dataset.status = status;

  const spinner = overlay.querySelector(`#${requestType}_spinner`);
  const tick = overlay.querySelector(`#${requestType}_tick`);

  if (!spinner || !tick) return;

  spinner.style.display = 'none';
  tick.style.display = 'none';

  if (status === 'requested' || status === 'load') {
      spinner.style.display = 'block';
  } else if (['wilco', 'executed', 'closed'].includes(status)) {
      tick.style.display = 'block';
  }
}