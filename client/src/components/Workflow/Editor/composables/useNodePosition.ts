import { useElementBounding } from "@vueuse/core";
import { type ComputedRef, onUnmounted, type Ref, unref, watch } from "vue";

import { type useWorkflowStateStore } from "@/stores/workflowEditorStateStore";

export function useNodePosition(
    nodeRef: Ref<HTMLElement | null>,
    stepId: number,
    workflowStateStore: ReturnType<typeof useWorkflowStateStore>,
    scale: ComputedRef<number> | Ref<number>
) {
    const position = useElementBounding(nodeRef, { windowResize: false });

    watch(
        Object.values(position),
        () => {
            workflowStateStore.setStepPosition(stepId, {
                height: unref(position.height) / scale.value,
                width: unref(position.width) / scale.value,
                left: unref(position.left) / scale.value,
                right: unref(position.right) / scale.value,
                top: unref(position.top) / scale.value,
                bottom: unref(position.bottom) / scale.value,
                x: unref(position.x) / scale.value,
                y: unref(position.y) / scale.value,
                update: position.update,
            });
        },
        { immediate: true }
    );

    onUnmounted(() => {
        workflowStateStore.deleteStepPosition(stepId);
    });
    return position;
}
