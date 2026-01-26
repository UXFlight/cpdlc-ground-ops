import { actionEvent } from "../events/action.js";
import { updateDirection } from "../state/state.js";
import { WORKFLOW_BUTTONS } from "../consts/buttonsWorkflow.js";
import { ALL_ACTIONS, LOADABLE_REQUEST_TYPES, REQUEST_TYPE } from "../consts/flightConsts.js";
import { MSG_STATUS } from "../consts/status.js";
import { CLASS_NAMES, SELECTORS } from "../consts/cssConsts.js";

// enabling btns based on action and requestType
export function enableButtonsByStatus(status, requestType) {
    switch (status) {
        case MSG_STATUS.LOADED:
            if (requestType === "DM_135") return setExecuteButtonState() // enables exec & cancel exec btn
            enableWilcoButtons(requestType);
            break;
        case MSG_STATUS.EXECUTED: 
            enableLoadButton(requestType)
            enableWilcoButtons(requestType) // enables wilco, standby, unable 
            break;
        case MSG_STATUS.CANCEL:
            setExecuteButtonState(true);
            enableRequestButton(requestType);
            break;
        case MSG_STATUS.UNABLE:
            enableRequestButton(requestType);
        default:
            break;
    }
}

// buttons functions
export function disableCancelButtons(requestType) {
    const cancelBtn = document.querySelector(SELECTORS.CANCEL_BUTTON_BY_REQUESTTYPE(requestType));
    if (cancelBtn) cancelBtn.disabled = true;
}

export const disableAllRequestButtons = () => {
    const requestButtons = document.querySelectorAll(SELECTORS.REQUEST_BUTTONS);
    requestButtons.forEach(btn => {
        btn.disabled = true;
        btn.classList.remove(CLASS_NAMES.ACTIVE);
    });
}

export const enableAllRequestButtons = () => {
    const requestButtons = document.querySelectorAll(SELECTORS.REQUEST_BUTTONS);
    requestButtons.forEach(btn => {
    if (btn.id === "pushback-btn") return; //! skip pushback, direction buttons will handle it
        btn.disabled = false;
        btn.classList.add(CLASS_NAMES.ACTIVE);
    });
};

export function createButton(requestType, status, message = '') {
    if (message) return 
    const btnContainer = document.createElement('div');
    btnContainer.classList.add(CLASS_NAMES.ACTION_BUTTONS_GROUP);

    const available = WORKFLOW_BUTTONS[requestType]?.[status]
    || WORKFLOW_BUTTONS.default[status?.toUpperCase()] // display only wilco/ unable if status is standby
    || WORKFLOW_BUTTONS.default.NEW;

    const actionsToShow = !LOADABLE_REQUEST_TYPES.includes(requestType)

    ? Object.entries(ALL_ACTIONS) 
            .filter(([action]) => ['WILCO', 'STANDBY', 'UNABLE'].includes(action)) 
    : Object.entries(ALL_ACTIONS)
    for (const [action, { id }] of actionsToShow) {
        const disabled = !available.includes(action);
        const btn = createActionButton(requestType, action, id, disabled);
        btnContainer.appendChild(btn);
    }

    return btnContainer;
}

function createActionButton(requestType, action, id = null, disabled = false) {
    const btn = document.createElement('button');
    btn.classList.add(CLASS_NAMES.ACTION_BUTTON);
    btn.textContent = action.toUpperCase();
    if (id) btn.id = id + `-${requestType}`;
    btn.dataset.actionType = action.toLowerCase();
    btn.disabled = disabled;
    btn.addEventListener('click', (e) => actionEvent(e));
    return btn;
}

// enables loadButton
export function enableLoadButton(requestType) {
    const loadButton = document.querySelector(SELECTORS.LOAD_BUTTON(requestType));
    if (loadButton) loadButton.disabled = false;
}

// enables wilcoButtons
export function enableWilcoButtons(requestType) {
    const wilcoButton = document.querySelector(SELECTORS.WILCO_BUTTON(requestType));
    const standbyButton = document.querySelector(SELECTORS.STANDBY_BUTTON(requestType));
    const unableButton = document.querySelector(SELECTORS.UNABLE_BUTTON(requestType));
    if (wilcoButton) wilcoButton.disabled = false;
    if (standbyButton) standbyButton.disabled = false;
    if (unableButton) unableButton.disabled = false;
}

// enables executeButtons
export function setExecuteButtonState(isDisabled = false) {
    const executeButton = document.querySelector(SELECTORS.EXECUTE_TAXI_CLEARANCE);
    const cancelExecuteButton = document.querySelector(SELECTORS.CANCEL_EXECUTE_TAXI_CLEARANCE);

    if (executeButton) executeButton.disabled = isDisabled;
    if (cancelExecuteButton) cancelExecuteButton.disabled = isDisabled;
}

// enables request button
export function enableRequestButton(requestType) {
    const requestButton = document.querySelector(SELECTORS.REQUEST_BTN_ID(requestType));

    if (!requestButton) return;
    if (requestType !== REQUEST_TYPE.PUSHBACK) return requestButton.disabled = false;

    const directionButtons = document.querySelectorAll(SELECTORS.DIRECTION_BUTTONS);
    directionButtons.forEach(btn => {
        btn.classList.remove(CLASS_NAMES.ACTIVE);
        btn.disabled = false
    });
}

//toggle pushback state
export function togglePushbackState(isCancelled = false, direction = "") {
    const pushBackRequest = document.querySelector(SELECTORS.PUSHBACK_REQUEST_BUTTON);
    const pushBackCancel = document.querySelector(SELECTORS.PUSHBACK_CANCEL_BUTTON);
    const pushBackDir = document.querySelector(SELECTORS.PUSHBACK_DIRECTION);
    const label = document.querySelector(SELECTORS.OVERLAY_TITLE_LABEL);

    updateDirection(direction);

    if (isCancelled) {
        pushBackDir.style.display = "flex";
        pushBackRequest.disabled = true;
        pushBackCancel.disabled = true;
        [pushBackCancel, pushBackRequest].forEach(btn => btn.style.display = "none");
        ["pushback-left", "pushback-right"].forEach(id => {
            const button = document.querySelector(SELECTORS.BY_ID(id));
            if (button) button.disabled = false;
        });
        label.textContent = "Pushback";
        return;
    }

    pushBackDir.style.display = "none";
    [pushBackCancel, pushBackRequest].forEach(btn => {
        btn.disabled = false;
        btn.style.display = "block"
    });
    ["pushback-left", "pushback-right"].forEach(id => document.querySelector(SELECTORS.BY_ID(id)).disabled = true);
    label.textContent = `Pushback ${direction.toUpperCase()}`;
}
