import { computed, inject, type Ref, unref } from "vue";

import { useWorkflowStores } from "@/composables/workflowStores";

import { DeleteSelectionAction, DuplicateSelectionAction } from "../Actions/workflowActions";
import { useMultiSelect } from "../composables/multiSelect";

export function useSelectionOperations() {
    const { undoRedoStore } = useWorkflowStores();
    const { anySelected, selectedCommentsCount, selectedStepsCount, deselectAll } = useMultiSelect();

    const selectedCountText = computed(() => {
        const stepWord = selectedStepsCount.value > 1 ? "步骤" : "步骤";
        const commentWord = selectedCommentsCount.value > 1 ? "注释" : "注释";
        let text = "已选择 ";

        if (selectedStepsCount.value > 0) {
            text += `${selectedStepsCount.value} 个${stepWord}`;

            if (selectedCommentsCount.value > 0) {
                text += " 和 ";
            }
        }

        if (selectedCommentsCount.value > 0) {
            text += `${selectedCommentsCount.value} 个${commentWord}`;
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
