import { setClearance } from "../state/clearance.js";
import { updateTaxiClearanceMsg } from "../ui/ui.js";

export function updateClearance(data) {
  const { kind, instruction } = data;
  setClearance(kind, instruction);
  updateTaxiClearanceMsg();
}