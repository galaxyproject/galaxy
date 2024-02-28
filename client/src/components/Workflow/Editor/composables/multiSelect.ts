import { useWorkflowStores } from "@/composables/workflowStores";

export function useMultiSelect() {
    const { commentStore, stateStore } = useWorkflowStores();

    function deselectAll() {
        commentStore.clearMultiSelectedComments();
        stateStore.clearStepMultiSelection();
    }

    return {
        deselectAll,
    };
}
