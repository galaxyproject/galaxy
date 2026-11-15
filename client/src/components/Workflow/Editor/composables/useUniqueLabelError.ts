import { computed, type MaybeRefOrGetter, toValue } from "vue";

import type { useWorkflowStepStore } from "@/stores/workflowStepStore";

export function useUniqueLabelError(
    workflowStateStore: ReturnType<typeof useWorkflowStepStore>,
    label: MaybeRefOrGetter<string | null | undefined>,
) {
    return computed(() => {
        const currentLabel = toValue(label);
        if (currentLabel && workflowStateStore.workflowOutputs[currentLabel]) {
            return `Duplicate label ${currentLabel}. Please fix this before saving the workflow.`;
        }
        return null;
    });
}
