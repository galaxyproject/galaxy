import { ref } from "vue";

import { type useWorkflowStepStore } from "@/stores/workflowStepStore";

export function useUniqueLabelError(
    workflowStateStore: ReturnType<typeof useWorkflowStepStore>,
    label: string | null | undefined
) {
    const error = ref<string | null>(null);
    if (label && workflowStateStore.workflowOutputs[label]) {
        error.value = `重复的标签 ${label}。请在保存工作流之前修复此问题。`;
    }
    return error;
}
