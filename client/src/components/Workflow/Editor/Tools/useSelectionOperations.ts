import { computed, inject, type Ref, unref } from "vue";

import { InsertStepAction } from "@/components/Workflow/Editor/Actions/stepActions";
import { getModule } from "@/components/Workflow/Editor/modules/services";
import { convertOpenConnections } from "@/components/Workflow/Editor/Tools/modules/convertOpenConnections";
import { removeOpenConnections } from "@/components/Workflow/Editor/Tools/modules/removeOpenConnections";
import { getTraversedSelection } from "@/components/Workflow/Editor/Tools/modules/traversedSelection";
import { Services } from "@/components/Workflow/services";
import { useWorkflowStores } from "@/composables/workflowStores";
import type { WorkflowComment } from "@/stores/workflowEditorCommentStore";
import { ensureDefined } from "@/utils/assertions";

import { DeleteSelectionAction, DuplicateSelectionAction } from "../Actions/workflowActions";
import { useMultiSelect } from "../composables/multiSelect";

export function useSelectionOperations() {
    const { undoRedoStore, stateStore, commentStore, stepStore, searchStore } = useWorkflowStores();
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

        const comments = commentIds.map((id) =>
            structuredClone(ensureDefined(commentStore.commentsRecord[id]))
        ) as WorkflowComment[];

        const stepArray = stepIds.map((id) => ensureDefined(stepStore.steps[id]));
        const stepEntriesWithFilteredInputs = removeOpenConnections(stepArray);

        const steps = Object.fromEntries(stepEntriesWithFilteredInputs.map((step) => [step.id, step]));

        const partialWorkflow = { comments, steps, name: "TODO: store name", id, annotation: "" };
        const newWf = await services.createWorkflow(partialWorkflow);

        return newWf;
    }

    async function moveSelectionToSubworkflow() {
        const stepIds = [...stateStore.multiSelectedStepIds];
        const commentIds = [...commentStore.multiSelectedCommentIds];

        const comments = commentIds.map((id) =>
            structuredClone(ensureDefined(commentStore.commentsRecord[id]))
        ) as WorkflowComment[];

        const expandedSelection = getTraversedSelection(stepIds, stepStore.steps);
        const {
            stepArray,
            inputReconnectionMap,
            outputReconnectionMap: _o,
        } = await convertOpenConnections(expandedSelection, stepStore.steps, searchStore);
        const stepEntriesWithFilteredInputs = removeOpenConnections(stepArray);

        const steps = Object.fromEntries(stepEntriesWithFilteredInputs.map((step) => [step.id, step]));

        const partialWorkflow = { comments, steps, name: "Extracted Subworkflow Test", id, annotation: "" };
        const newWf = await services.createWorkflow(partialWorkflow);

        // ---------------

        commentIds.forEach((id) => {
            commentStore.deleteComment(id);
        });

        commentStore.clearMultiSelectedComments();

        expandedSelection.forEach((id) => {
            stepStore.removeStep(id);
        });

        stateStore.clearStepMultiSelection();

        // -------------

        const action = new InsertStepAction(stepStore, stateStore, {
            contentId: newWf.latest_workflow_id,
            name: newWf.name,
            type: "subworkflow",
            position: { top: 0, left: 0 },
        });

        undoRedoStore.applyAction(action);
        const stepData = action.getNewStepData();

        const response = await getModule(
            { name: newWf.name, type: "subworkflow", content_id: newWf.latest_workflow_id },
            stepData.id,
            stateStore.setLoadingState
        );

        const updatedStep = {
            ...stepData,
            tool_state: response.tool_state,
            inputs: response.inputs,
            input_connections: inputReconnectionMap,
            outputs: response.outputs,
            config_form: response.config_form,
        };

        stepStore.updateStep(updatedStep);
        action.updateStepData = updatedStep;

        stateStore.activeNodeId = stepData.id;

        return newWf;
    }

    return {
        anySelected,
        deselectAll,
        selectedCountText,
        deleteSelection,
        duplicateSelection,
        copySelectionToNewWorkflow,
        moveSelectionToSubworkflow,
    };
}
