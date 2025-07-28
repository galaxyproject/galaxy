import { onAllInputs } from "@/components/Workflow/Editor/modules/onAllInputs";
import type { Step } from "@/stores/workflowStepStore";
import { ensureDefined } from "@/utils/assertions";

function exploreBranch(branchToExplore: number, selectedKeys: Set<number>, allSteps: Record<number, Step>): number[] {
    if (selectedKeys.has(branchToExplore)) {
        return [branchToExplore];
    }

    const step = ensureDefined(allSteps[branchToExplore]);

    let collidingChildKeys: number[] = [];
    const expandedSelection = new Set(selectedKeys);

    onAllInputs(step, (connection) => {
        const collidingKeys = exploreBranch(connection.id, expandedSelection, allSteps);
        collidingKeys.forEach((key) => expandedSelection.add(key));
        collidingChildKeys = [...collidingChildKeys, ...collidingKeys];
    });

    if (collidingChildKeys.length > 0) {
        return [...collidingChildKeys, branchToExplore];
    } else {
        return [];
    }
}

/** Expands a selection by traversing connected nodes and including open loops */
export function getTraversedSelection(selectedKeys: number[], allSteps: Record<number, Step>): number[] {
    const selection = selectedKeys.map((key) => ensureDefined(allSteps[key]));

    const expandedSelection = new Set(selectedKeys);

    selection.forEach((step) => {
        onAllInputs(step, (connection) => {
            const addedToSelection = exploreBranch(connection.id, expandedSelection, allSteps);
            addedToSelection.forEach((key) => expandedSelection.add(key));
        });
    });

    return Array.from(expandedSelection);
}
