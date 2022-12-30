import { useElementBounding } from "@vueuse/core";
import { onUnmounted, reactive, type Ref } from "vue";
import type { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";

export function useNodePosition(
    nodeRef: Ref<HTMLElement | null>,
    stepId: number,
    workflowStateStore: ReturnType<typeof useWorkflowStateStore>
) {
    const position = useElementBounding(nodeRef, { windowResize: false });
    workflowStateStore.setStepPosition(stepId, reactive(position));
    onUnmounted(() => {
        workflowStateStore.deleteStepPosition(stepId);
    });
    return position;
}
