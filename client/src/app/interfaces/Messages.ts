import { PushbackDirection } from "./Payloads";

export type StepCode = 'DM_136' | 'DM_134' | 'DM_131' | 'DM_135' | 'DM_127';
export type QuickResponse = 'AFFIRM' | 'STANDBY' | 'UNABLE';

const QUICK_RESPONSES: Record<StepCode, Partial<Record<QuickResponse, string>>> = {
  DM_136: { // Expected Taxi Clearance
    AFFIRM: 'Expected taxi routing approved.',
    STANDBY: 'Standby for expected taxi routing.',
    UNABLE: 'Unable to approve expected taxi routing.'
  },
  DM_134: { // Engine Startup
    AFFIRM: "Cleared to start engine. ",
    STANDBY: "Standby for engine start clearance.",
    UNABLE: "Unable to approve engine start."
  },
  DM_131: { // Pushback
    AFFIRM: "Pushback approved. Start when ready.",
    STANDBY: "Standby for pushback clearance.",
    UNABLE: "Unable to approve pushback."
  },
  DM_135: { // Taxi Clearance
    AFFIRM: 'Taxi clearance approved. Proceed as instructed.',
    STANDBY: 'Standby for taxi clearance.',
    UNABLE: 'Unable to approve taxi clearance at this time.'
  },
  DM_127: { // De-Icing
    AFFIRM: "De-icing approved. Proceed to de-icing pad.",
    STANDBY: "Standby for de-icing instructions.",
    UNABLE: "Unable to approve de-icing at this time."
  }
};

export const formatQuickResponse = (
    quick: QuickResponse,
    stepCode: StepCode,
    direction?: PushbackDirection
): string => {
    if (stepCode === 'DM_131' && direction) {
        const dir = direction.toUpperCase();
        const byDirection: Record<QuickResponse, string> = {
            AFFIRM: `Pushback ${dir} approved. Start when ready.`,
            STANDBY: `Standby for pushback ${dir} clearance.`,
            UNABLE: `Unable to approve pushback ${dir}.`
        };
        return byDirection[quick];
    }
    return QUICK_RESPONSES[stepCode]?.[quick] ?? '';
};

export const getQReponseByStepCode = (stepCode: StepCode): string[] => {
    return Object.keys(QUICK_RESPONSES[stepCode] ?? {});
}
