import { state } from "../state/state.js";
import { REQUEST_TYPE } from "./consts/flightConsts.js";

export function getRequestPayload(requestType) {
  switch (requestType) {
    case REQUEST_TYPE.PUSHBACK:
      const direction = state.steps[REQUEST_TYPE.PUSHBACK].direction;
      if (!direction) throw new Error("Pushback direction not selected");
      return { direction };
    default:
      return {};
  }
}
