import { displayHistoryLogs } from "../events/filter.js";
import { filterEvent } from "../events/filter.js";
import { CLASS_NAMES, SELECTORS } from "../consts/cssConsts.js";

const config = {
    audioNotis : false,
    verboseLogs : false,
    autoBox: false,
    autoAck : false,
    autoRetry : false,
}

export const CONFIG_KEYS = {
    AUDIO: "audioNotis",
    UTC: "utcDisplay",
    TEMPERATURE: "tempReadings",
    LOGS: "verboseLogs",
    FILTER: "autoBox",
    ACK: "autoAck",
    RETRY: "autoRetry"
}

export const setConfig = () => {
    const toggleSwitch = document.querySelectorAll(SELECTORS.TOGGLE_SWITCHES);

    toggleSwitch.forEach((toggle) => {
        const key = toggle.dataset.setting;
        toggle.classList.toggle(CLASS_NAMES.ACTIVE, config[key]);
    })
    return;
}

export const toggleSwitchEvent = (e) => {
    const target = e.target.closest(SELECTORS.TOGGLE_SWITCHES);
    const key = target?.dataset.setting;
    if (target) target.classList.toggle(CLASS_NAMES.ACTIVE);
    if (key) config[key] = !config[key];
    if (key === CONFIG_KEYS.LOGS) displayHistoryLogs()
    if (key === CONFIG_KEYS.FILTER) {
        filterEvent()
    };
}

export const getBool = (key) =>{
    return config[key];
}

export const toggleFilter = () => {
    config[CONFIG_KEYS.FILTER] = !config[CONFIG_KEYS.FILTER];
}
