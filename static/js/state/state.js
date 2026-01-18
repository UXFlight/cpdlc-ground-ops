import { updateMessageStatus, updateOverlayStatus } from "../ui/ui.js";
import { REQUEST_TYPE } from "../consts/flightConsts.js";
import { markDashboardReady } from "./settingsState.js";

// Global state
export const state = {
  history: [],                // history logs
  connection: {
    connectedSince: null, // timestamp when the connection was established
    backend: "connecting",    // "connecting" | "connected" | "disconnected"
    atc: {
      status : "pending",     // "pending" | "connected" | "disconnected"
      facility: null, 
    },
  },
  steps: {
    DM_136: createStep("Expected Taxi Clearance"),
    DM_134: createStep("Engine Startup"),
    DM_131: createStep("Pushback", { direction: null }),
    DM_135: createStep("Taxi Clearance"),
    DM_127: createStep("De-Icing"),
    DM_20: createStep("Request Voice Contact"), 
  },
};

function createStep(label, extra = {}) {
  return {
    label,
    status: null,
    message: null,
    timestamp: null,
    timeLeft : null,
    ...extra
  };
}

export function updateStep(requestType, newStatus, newMessage = null, timestamp = null, timeLeft = null, label = null) {
  const key = requestType;
  const step = state.steps[key];
  if (!step) return;

  const formattedTimestamp = formatToTime(timestamp || new Date().toISOString());

  const entry = {
    status: newStatus,
    message: newMessage,
    timestamp: formattedTimestamp
  };

  step.status = newStatus;
  step.label = label || step.label; // only to update label for pushback + DIRECTION
  step.message = newMessage;
  step.timestamp = formattedTimestamp;

  step.timeLeft = timeLeft;

  let group = state.history.find(h => h.stepKey === key);
  if (!group) {
    group = { stepKey: key, label: step.label, entries: [] };
    state.history.push(group);
  }
  group.entries.push(entry);

  updateMessageStatus(key, newStatus);
  updateOverlayStatus(key, newStatus);
  markDashboardReady();
}

function formatToTime(isoString) {
  try {
    const date = new Date(isoString);
    return date.toISOString().substr(11, 8); 
  } catch {
    return isoString;
  }
}

export function updateDirection(direction = null) {
  state.steps[REQUEST_TYPE.PUSHBACK].direction = direction;
  document.getElementById("pushback-left").classList.toggle("active", direction === "left");
  document.getElementById("pushback-right").classList.toggle("active", direction === "right");
}