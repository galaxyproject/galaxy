import { computed, inject, type Ref, unref } from "vue";

import { useWorkflowStores } from "@/composables/workflowStores";
import type { WorkflowComment } from "@/stores/workflowEditorCommentStore";
import { ensureDefined } from "@/utils/assertions";

import { useMultiSelect } from "../composables/multiSelect";
import { fromSimple } from "../modules/model";

export function useSelectionOperations() {
    const { commentStore, stateStore, stepStore } = useWorkflowStores();
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
        commentStore.multiSelectedCommentIds.forEach((id) => {
            commentStore.deleteComment(id);
        });

        commentStore.clearMultiSelectedComments();

        stateStore.multiSelectedStepIds.forEach((id) => {
            stepStore.removeStep(id);
        });

        stateStore.clearStepMultiSelection();
    }

    const workflowId = inject("workflowId") as Ref<string> | string;
    const id = unref(workflowId);

    function duplicateSelection() {
        const commentIds = [...commentStore.multiSelectedCommentIds];
        const stepIds = [...stateStore.multiSelectedStepIds];

        deselectAll();

        const comments = commentIds.map((id) =>
            structuredClone(ensureDefined(commentStore.commentsRecord[id]))
        ) as WorkflowComment[];

        const steps = Object.fromEntries(
            stepIds.map((id) => [id, structuredClone(ensureDefined(stepStore.steps[id]))])
        );

        fromSimple(id, { comments, steps }, true, { top: 50, left: 100 }, true);
    }

    return {
        anySelected,
        deselectAll,
        selectedCountText,
        deleteSelection,
        duplicateSelection,
    };
}
