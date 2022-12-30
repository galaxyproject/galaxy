import type { useWorkflowStepStore } from "@/stores/workflowStepStore";
import { ref } from "vue";

export function useUniqueLabelError(workflowStateStore: ReturnType<typeof useWorkflowStepStore>, label: string) {
    const error = ref("");
    if (workflowStateStore.workflowOutputs[label]) {
        error.value = `Duplicate label ${label}. Please fix this before saving the workflow.`;
    } else {
        error.value = "";
    }
    return error;
}
