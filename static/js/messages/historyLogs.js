import { MSG_STATUS } from '../consts/status.js';
import { state } from '../state/state.js';
import { flashElement } from '../ui/ui.js';
import { createButton } from '../ui/buttons-ui.js';
import { createTimer } from '../ui/timer-ui.js';
import { getBool, CONFIG_KEYS } from '../state/configState.js';
import { CLASS_NAMES, SELECTORS } from '../consts/cssConsts.js';

//DOM UTILITIES //
const historyLogBox = document.querySelector(SELECTORS.HISTORY_LOG_BOX);


export function createGroupedLog({ stepKey, label, latest, history }) {
    const div = document.createElement('div');
    div.classList.add(CLASS_NAMES.NEW_MESSAGE);
    div.dataset.requesttype = stepKey;
    div.dataset.status = latest.status;
    div.style.cursor = 'pointer';

    const showLogs = getBool(CONFIG_KEYS.LOGS);
    const historyContainer = showLogs ? createHistoryDetails(history.slice(0, -1)) : null;

    const header = createHeader({
        timestamp: latest.timestamp,
        title: label,
        status: latest.status,
        historyContainer,
        showToggle: showLogs,
        stepKey: stepKey
    });


    div.appendChild(header);

    if (latest.message) {
        div.appendChild(createResponseParagraph(latest.message));
    }

    if (historyContainer) {
        div.appendChild(historyContainer);
    }

    const hasButtons = [MSG_STATUS.NEW, MSG_STATUS.LOADED, MSG_STATUS.EXECUTED, MSG_STATUS.STANDBY].includes(latest.status);

    if (hasButtons) {
        const message = latest.message.startsWith('Standby') ? latest.message : '';
        const btn = createButton(stepKey, latest.status, message)
        if (btn) div.appendChild(createButton(stepKey, latest.status, message));
        flashElement(div);
    }

    historyLogBox.prepend(div);
}

// SUBCOMPONENTS //
function createHeader({ timestamp, title, status, historyContainer, showToggle, stepKey }) {
    const p = document.createElement('p');

    const ts = document.createElement('span');
    ts.className = 'timestamp';
    ts.textContent = timestamp;

    const titleEl = document.createElement('span');
    titleEl.className = 'message-title';
    titleEl.textContent = title;

    const statusEl = document.createElement('span');
    statusEl.className = `status ${status}`;
    statusEl.textContent = status.toUpperCase();

    p.append(statusEl, titleEl, ts);
    const step = state.steps[stepKey];

    const statusIsDone = [MSG_STATUS.EXECUTED, MSG_STATUS.TIMEOUT, MSG_STATUS.CANCELLED, MSG_STATUS.ERROR, MSG_STATUS.CLOSED, MSG_STATUS.UNABLE, MSG_STATUS.CANCEL]
        .includes(status.toLowerCase());

    const showTimer = step?.timeLeft && !statusIsDone;

    if (showTimer) {
        p.appendChild(createTimer(stepKey, step.timeLeft));
    }

    if (showToggle && historyContainer) {
        const toggle = document.createElement('span');
        toggle.className = 'toggle-arrow';
        toggle.textContent = '▾';
        toggle.style.marginLeft = '10px';
        p.appendChild(toggle);

        p.addEventListener("click", (e) => {
            e.stopPropagation();
            const isOpen = historyContainer.style.display === 'block';
            historyContainer.style.display = isOpen ? 'none' : 'block';
            toggle.textContent = isOpen ? '▾' : '▴';
        });
    }

    return p;
}

function createResponseParagraph(message) {
    const p = document.createElement('p');
    p.className = 'message-response';
    p.textContent = message;
    return p;
}

function createHistoryDetails(historyEntries) {
    const container = document.createElement('div');
    container.className = 'history-details';
    container.style.display = 'none';

    historyEntries.forEach(entry => {
        const p = document.createElement('p');
        p.className = 'message-response';
        p.innerText = `(${entry.timestamp}) ${entry.status.toUpperCase()}: ${entry.message || "--"}`;
        container.appendChild(p);
    });

    return container;
}

// MESSAGE RESPONSE INSERTION //
export function createResponse(message, div) {
    const response = createResponseParagraph(message);
    div.append(response);
}
