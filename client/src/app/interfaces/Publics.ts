import { StepStatus } from "./StepStatus";

// PLANE
export type LonLat = [number, number];

export interface LocationInfo {
  name: string;
  type: "parking" | "taxiway" | "runway";
  coord: LonLat;
}

export interface Plane {
  spawn_pos: LocationInfo;
  current_pos: LocationInfo;
  final_pos: LocationInfo;
  current_heading: number;
  current_speed: number;
}

// STEP
export interface StepPublicView {
    step_code: string;
    label: string;
    status: StepStatus;
    message: string;
    timestamp: number;
    validated_at: number;
    request_id: string;
    time_left: number | null;
}

export interface StepEvent {
    step_code: string;
    status: StepStatus;
    timestamp: number;
    message: string | null;
    request_id: string;
}

// CLEARANCE
export type ClearanceType = "expected" | "taxi" | "route_change";

export interface Clearance {
  kind: ClearanceType;
  instruction: string;
  coords: LocationInfo[];
  issued_at: string;
}

export interface PilotPublicView {
    sid: string;
    steps: Record<string, StepPublicView>;
    color: string;
    history: StepEvent[];
    plane: Plane;
    clearances: Record<string, Clearance>;   

    // frontend specific
    notificationCount: number;
    renderClearance?: boolean;
}

// NEW REQUEST
export interface AckUpdatePayload {
    pilot_sid: string;
    step_code: string;
    label?: string;
    status: StepStatus;
    message: string;
    validated_at: number;
    request_id: string,
    time_left?: number
}

// NEW CLEARANCE
export interface ClearancePayload {
    pilot_sid: string;
    clearance: Clearance;
}

export interface ClearancesCancelledPayload {
  pilot_sid: string;
  clearances: Record<ClearanceType, Clearance>;
}