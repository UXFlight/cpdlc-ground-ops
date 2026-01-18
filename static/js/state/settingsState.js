import { state } from "./state.js";
import { CLASS_NAMES, SELECTORS } from "../consts/cssConsts.js";

export const dashboardState = {
    sid: null,
    dashboardNeedsRefresh: false,
};

export function dashboardNeedsRefresh() {
    return dashboardState.dashboardNeedsRefresh;
}

export function setConnectionInfos(sid, connectedSince) {
    dashboardState.sid = sid;
    state.connection.connectedSince = connectedSince;
    markDashboardReady();
}

export function markDashboardReady() {
    const panel = document.querySelector(SELECTORS.SETTINGS_PANEL);
    dashboardState.dashboardNeedsRefresh = true;
    if (panel && panel.classList.contains(CLASS_NAMES.ACTIVE)) updateDashboardPanel();
}

export const updateDashboardPanel = () => {
    if (!dashboardState.dashboardNeedsRefresh) return;
    dashboardState.dashboardNeedsRefresh = false;

    document.querySelector(SELECTORS.DASHBOARD_SID).textContent = dashboardState.sid ?? "Pilot Settings";
    document.querySelector(SELECTORS.DASHBOARD_ATC).textContent = state.connection.atc.facility ?? "ATC  Facility";

    // document.querySelector(SELECTORS.DASHBOARD_MESSAGES).textContent = getMessageCount();
};

// const getMessageCount = () => {
//     return state.history.reduce((count, group) => count + group.entries.length, 0);
// }
