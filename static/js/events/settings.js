import { dashboardNeedsRefresh, updateDashboardPanel } from "../state/settingsState.js";
import { CLASS_NAMES, SELECTORS } from "../consts/cssConsts.js";

export const settingEvent = (e) => {
  e.preventDefault();
  e.stopPropagation();

  const panel = document.querySelector(SELECTORS.SETTINGS_PANEL);
  panel.classList.toggle(CLASS_NAMES.ACTIVE);

  const isVisible = panel.classList.contains(CLASS_NAMES.ACTIVE);
  if (isVisible && dashboardNeedsRefresh()) updateDashboardPanel();
};

export const closeSettingsButton = () => {
  const panel = document.querySelector(SELECTORS.SETTINGS_PANEL);
  if (panel.classList.contains(CLASS_NAMES.ACTIVE)) {
    panel.classList.remove(CLASS_NAMES.ACTIVE);
  }
}
