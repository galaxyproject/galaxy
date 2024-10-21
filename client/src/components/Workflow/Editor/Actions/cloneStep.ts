import { type Step, type WorkflowStepStore } from "@/stores/workflowStepStore";

/**
 * Copies a step and increments a trailing number in it's label,
 * or adds said trailing number
 *
 * @param step step to clone
 * @param labelSet set containing all labels. Will me mutated to include new label
 * @returns cloned step
 */
export function cloneStepWithUniqueLabel(step: Readonly<Step>, labelSet: Set<string>): Step {
    const newStep = structuredClone(step) as Step;

    if (newStep.label) {
        while (labelSet.has(newStep.label)) {
            const number = newStep.label.match(/[0-9]+$/)?.[0];

            if (number) {
                const count = parseInt(number);
                newStep.label = newStep.label?.replace(/[0-9]+$/, `${count + 1}`);
            } else {
                newStep.label += " 2";
            }
        }

        labelSet.add(newStep.label);
    }

    return newStep;
}

export function getLabelSet(store: WorkflowStepStore): Set<string> {
    const steps = Object.values(store.steps);
    const labels = steps.flatMap((step) => (step.label ? [step.label] : []));
    return new Set(labels);
}
