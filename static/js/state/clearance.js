const clearance = {
    "expected": "",
    "taxi": "",
    "route_change": "",
}

export const setClearance = (kind, instruction) => {
  clearance[kind] = instruction;
}

export const getRecentClearance = () => {
  if (clearance.route_change) return { kind: "route_change", instruction: clearance.route_change };
  if (clearance.taxi) return { kind: "taxi", instruction: clearance.taxi };
  if (clearance.expected)  return { kind: "expected", instruction: clearance.expected };
  return null;
};