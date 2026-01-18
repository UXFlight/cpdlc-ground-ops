import { state, updateDirection } from "../state/state.js";
import { createGroupedLog } from "../messages/historyLogs.js";
import { clearMessageBox } from "../ui/ui.js";
import { MSG_STATUS } from '../consts/status.js';
import { STATUS_PRIORITY } from "../consts/priorityConsts.js";
import { CONFIG_KEYS, getBool, toggleFilter } from "../state/configState.js";
import { REQUEST_TYPE } from "../consts/flightConsts.js";

export const filterEvent = () => {
  const hasClosableLogs = state.history.some(
    log => [MSG_STATUS.CLOSED, MSG_STATUS.UNABLE].includes(
      log.entries[log.entries.length - 1].status
    )
  );

  if (!hasClosableLogs) return;
  displayHistoryLogs()
}

export const displayHistoryLogs = () => {
  clearMessageBox();
  const logs = state.history.map(group => {
    const latest = group.entries[group.entries.length - 1];

    const stepLabel = state.steps?.[group.stepKey]?.label;
    const label = (latest && latest.label) ?? stepLabel ?? group.label;

    return {
      stepKey: group.stepKey,
      label: label,
      latest,
      history: group.entries,
    };
  });

  const visibleLogs = getBool(CONFIG_KEYS.FILTER)
    ? logs.filter(log =>
        ![MSG_STATUS.CLOSED, MSG_STATUS.UNABLE, MSG_STATUS.CANCEL, MSG_STATUS.CANCELLED, MSG_STATUS.ERROR, MSG_STATUS.TIMEOUT].includes(log.latest.status)
      )
    : logs;

  visibleLogs.sort((a, b) => {
    const pA = STATUS_PRIORITY[a.latest.status] ?? -99;
    const pB = STATUS_PRIORITY[b.latest.status] ?? -99;

    if (pA !== pB) return pA - pB;
    const tA = a.latest.timestamp ?? -1;
    const tB = b.latest.timestamp ?? -1;
  
    return tB - tA;
  });

  visibleLogs.forEach(createGroupedLog);
};
