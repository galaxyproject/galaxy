import { computed, inject, type Ref, unref } from "vue";

import { useWorkflowStores } from "@/composables/workflowStores";

import { DeleteSelectionAction, DuplicateSelectionAction } from "../Actions/workflowActions";
import { useMultiSelect } from "../composables/multiSelect";

export function useSelectionOperations() {
    const { undoRedoStore } = useWorkflowStores();
    const { anySelected, selectedCommentsCount, selectedStepsCount, deselectAll } = useMultiSelect();

    const selectedCountText = computed(() => {
        const stepWord = selectedStepsCount.value > 1 ? "steps" : "step";
        const commentWord = selectedCommentsCount.value > 1 ? "comments" : "comment";
        let text = "selected ";

        if (selectedStepsCount.value > 0) {
            text += `${selectedStepsCount.value} ${stepWord}`;

            if (selectedCommentsCount.value > 0) {
                text += " and ";
            }
        }

        if (selectedCommentsCount.value > 0) {
            text += `${selectedCommentsCount.value} ${commentWord}`;
        }

        return text;
    });

    function deleteSelection() {
        undoRedoStore.applyAction(new DeleteSelectionAction(id));
    }

    const workflowId = inject("workflowId") as Ref<string> | string;
    const id = unref(workflowId);

    function duplicateSelection() {
        undoRedoStore.applyAction(new DuplicateSelectionAction(id));
    }

    return {
        anySelected,
        deselectAll,
        selectedCountText,
        deleteSelection,
        duplicateSelection,
    };
}
