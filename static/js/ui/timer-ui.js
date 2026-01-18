import { CLASS_NAMES, SELECTORS } from "../consts/cssConsts.js";

  const FULL_DASH_ARRAY = 113;

  const COLOR_CODES = {
    info: "#3498db",
    warning: "#6ec6ff",
    alert: "#90caf9"
  };
  
  function getColorForTime(timeLeft, total = 90) {
    const warningThreshold = total * 0.33;
    const alertThreshold = total * 0.1;

    if (timeLeft <= alertThreshold) return COLOR_CODES.alert;
    if (timeLeft <= warningThreshold) return COLOR_CODES.warning;
    return COLOR_CODES.info;
  }

  function getColorClass(timeLeft, total = 90) {
    const warningThreshold = total * 0.33;
    const alertThreshold = total * 0.1;

    if (timeLeft <= alertThreshold) return "alert";
    if (timeLeft <= warningThreshold) return "warning";
    return "info";
  }

  export function createTimer(requestType, timeLeft, total = 90) {
    const wrapper = document.createElement('div');
    wrapper.className = 'circular-timer';
    wrapper.id = `${requestType}_timer`;

    const percent = timeLeft / total;
    const offset = FULL_DASH_ARRAY * (1 - percent);
    const color = getColorForTime(timeLeft, total);
    const className = getColorClass(timeLeft, total);

    wrapper.innerHTML = `
      <svg viewBox="0 0 40 40">
        <circle class="bg" r="18" cx="20" cy="20"></circle>
        <circle class="progress ${className}" r="18" cx="20" cy="20"
          stroke-dasharray="${FULL_DASH_ARRAY}"
          stroke-dashoffset="${offset}"
          stroke="${color}"></circle>
      </svg>
      <div class="time-left">${timeLeft}</div>
    `;

    return wrapper;
  }

  export function updateTimerVisual(requestType, timeLeft, total) {
    const timer = document.querySelector(SELECTORS.REQUEST_TIMER(requestType));
    if (!timer) {
      console.warn(`[TIMER] No element found for: ${requestType}_timer`);
      return;
    }

    const percent = timeLeft / total;
    const offset = FULL_DASH_ARRAY * (1 - percent);
    const color = getColorForTime(timeLeft, total);
    const className = getColorClass(timeLeft, total);

    const progress = timer.querySelector('.progress');
    const text = timer.querySelector('.time-left');

    if (progress) {
      progress.setAttribute('stroke-dashoffset', offset);
      progress.setAttribute('stroke', color);

      progress.classList.remove(CLASS_NAMES.INFO, CLASS_NAMES.WARNING, CLASS_NAMES.ALERT);
      progress.classList.add(className);
    }

    if (text) {
      text.textContent = timeLeft;
    }
  }
