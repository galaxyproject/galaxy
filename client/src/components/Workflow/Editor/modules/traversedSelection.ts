import { onAllInputs } from "@/components/Workflow/Editor/modules/onAllInputs";
import type { Step } from "@/stores/workflowStepStore";
import { ensureDefined } from "@/utils/assertions";

/**
 * Expands a selection by including every step that sits between selected steps,
 * i.e. is fed by the selection and feeds back into it.
 */
export function getTraversedSelection(selectedKeys: number[], allSteps: Record<number, Step>): number[] {
    const selected = new Set(selectedKeys);
    // whether a step leads back into the selection; cached so shared upstream steps are explored once
    const leadsToSelection = new Map<number, boolean>();

    function reachesSelection(stepId: number): boolean {
        if (selected.has(stepId)) {
            return true;
        }

        const cached = leadsToSelection.get(stepId);
        if (cached !== undefined) {
            return cached;
        }

        let reaches = false;
        // explore every input, so all in-between steps on all paths get recorded
        onAllInputs(ensureDefined(allSteps[stepId]), (connection) => {
            if (reachesSelection(connection.id)) {
                reaches = true;
            }
        });

        leadsToSelection.set(stepId, reaches);
        return reaches;
    }

    selectedKeys.forEach((key) => {
        onAllInputs(ensureDefined(allSteps[key]), (connection) => reachesSelection(connection.id));
    });

    const inBetween = [...leadsToSelection].filter(([, reaches]) => reaches).map(([stepId]) => stepId);
    return [...selectedKeys, ...inBetween];
}
