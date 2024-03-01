import { computed } from "vue";

import { useWorkflowStores } from "@/composables/workflowStores";

export function useMultiSelect() {
    const { commentStore, stateStore } = useWorkflowStores();

    function deselectAll() {
        commentStore.clearMultiSelectedComments();
        stateStore.clearStepMultiSelection();
    }

    const selectedCommentsCount = computed(() => commentStore.multiSelectedCommentIds.length);
    const selectedStepsCount = computed(() => stateStore.multiSelectedStepIds.length);
    const anySelected = computed(() => selectedCommentsCount.value > 0 || selectedStepsCount.value > 0);

    return {
        selectedCommentsCount,
        selectedStepsCount,
        anySelected,
        deselectAll,
    };
}
