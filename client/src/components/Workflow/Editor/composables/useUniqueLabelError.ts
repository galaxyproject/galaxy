import { computed, type MaybeRefOrGetter, toValue } from "vue";

import type { useWorkflowStepStore } from "@/stores/workflowStepStore";

/** Error for a step label that another step of the workflow already uses. */
export function useUniqueLabelError(
    stepStore: ReturnType<typeof useWorkflowStepStore>,
    stepId: MaybeRefOrGetter<number>,
    label: MaybeRefOrGetter<string | null | undefined>,
) {
    return computed(() => {
        const currentLabel = toValue(label);
        const currentStepId = toValue(stepId);
        if (!currentLabel) {
            return null;
        }
        const isDuplicate = Object.values(stepStore.steps).some(
            (step) => step.id !== currentStepId && step.label === currentLabel,
        );
        return isDuplicate ? `Duplicate label ${currentLabel}. Please fix this before saving the workflow.` : null;
    });
}
