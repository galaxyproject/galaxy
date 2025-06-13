import { computed, inject, type Ref, unref } from "vue";

import { Services } from "@/components/Workflow/services";
import { useWorkflowStores } from "@/composables/workflowStores";
import type { WorkflowComment } from "@/stores/workflowEditorCommentStore";
import type { ConnectionOutputLink, Step } from "@/stores/workflowStepStore";
import { ensureDefined } from "@/utils/assertions";

import { DeleteSelectionAction, DuplicateSelectionAction } from "../Actions/workflowActions";
import { useMultiSelect } from "../composables/multiSelect";

export function useSelectionOperations() {
    const { undoRedoStore, stateStore, commentStore, stepStore } = useWorkflowStores();
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

    const services = new Services();

    async function copySelectionToNewWorkflow() {
        const commentIds = [...commentStore.multiSelectedCommentIds];
        const stepIds = [...stateStore.multiSelectedStepIds];

        const stepIdSet = new Set(stepIds);

        const comments = commentIds.map((id) =>
            structuredClone(ensureDefined(commentStore.commentsRecord[id]))
        ) as WorkflowComment[];

        const stepEntries: [number, Step][] = stepIds.map((id) => [id, ensureDefined(stepStore.steps[id])]);

        const stepEntriesWithFilteredInputs: [number, Step][] = stepEntries.map(([id, step]) => {
            const connectionEntries = Object.entries(step.input_connections);

            const filteredConnectionEntries: [string, ConnectionOutputLink[]][] = connectionEntries.flatMap(
                ([id, connection]) => {
                    if (!connection) {
                        return [];
                    }

                    const connectionArray = Array.isArray(connection) ? connection : [connection];
                    const filteredConnectionArray = connectionArray.filter((connection) =>
                        stepIdSet.has(connection.id)
                    );

                    if (filteredConnectionArray.length === 0) {
                        return [];
                    } else {
                        return [[id, filteredConnectionArray]];
                    }
                }
            );

            const input_connections = Object.fromEntries(filteredConnectionEntries);

            return [id, { ...step, input_connections }];
        });

        const steps = Object.fromEntries(stepEntriesWithFilteredInputs);

        const partialWorkflow = { comments, steps, name: "TODO: store name", id, annotation: "" };
        const newWf = await services.createWorkflow(partialWorkflow);

        return newWf;
    }

    return {
        anySelected,
        deselectAll,
        selectedCountText,
        deleteSelection,
        duplicateSelection,
        copySelectionToNewWorkflow,
    };
}
