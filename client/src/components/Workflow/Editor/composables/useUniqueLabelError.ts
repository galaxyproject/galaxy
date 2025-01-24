import { ref } from "vue";

import { type useWorkflowStepStore } from "@/stores/workflowStepStore";

export function useUniqueLabelError(
    workflowStateStore: ReturnType<typeof useWorkflowStepStore>,
    label: string | null | undefined
) {
    const error = ref<string | null>(null);
    if (label && workflowStateStore.workflowOutputs[label]) {
        error.value = `Duplicate label ${label}. Please fix this before saving the workflow.`;
    }
    return error;
}
