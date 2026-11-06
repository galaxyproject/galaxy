import { isWorkflowInput } from "@/components/Workflow/constants";
import { convertOpenConnections } from "@/components/Workflow/Editor/modules/convertOpenConnections";
import { removeOpenConnections } from "@/components/Workflow/Editor/modules/removeOpenConnections";
import { getTraversedSelection } from "@/components/Workflow/Editor/modules/traversedSelection";
import { useWorkflowStores } from "@/composables/workflowStores";
import type { WorkflowComment } from "@/stores/workflowEditorCommentStore";
import type { Step } from "@/stores/workflowStepStore";
import { ensureDefined } from "@/utils/assertions";

export interface PartialWorkflow {
    comments: WorkflowComment[];
    steps: {
        [key: string]: Step;
    };
    name: string;
    id: string;
    annotation: string;
}

export async function extractSubworkflow(workflowId: string, name: string) {
    const { stateStore, commentStore, stepStore, searchStore } = useWorkflowStores(workflowId);

    // input steps stay in the parent workflow, keeping their connections, and feed the subworkflow instead
    const selectedStepIds = [...stateStore.multiSelectedStepIds];
    const keptInputSteps = new Set(
        selectedStepIds.filter((id) => isWorkflowInput(ensureDefined(stepStore.steps[id]).type)),
    );
    const stepIds = selectedStepIds.filter((id) => !keptInputSteps.has(id));

    if (stepIds.length === 0) {
        throw new Error("Select at least one step that is not a workflow input to move into a sub-workflow");
    }

    const commentIds = [...commentStore.multiSelectedCommentIds];

    const expandedSelection = getTraversedSelection(stepIds, stepStore.steps);
    const expandedSteps = new Set(expandedSelection.filter((id) => !stepIds.includes(id)));

    const comments = commentIds.map((id) =>
        structuredClone(ensureDefined(commentStore.commentsRecord[id])),
    ) as WorkflowComment[];

    const { stepArray, inputReconnectionMap, outputReconnectionMap } = await convertOpenConnections(
        expandedSelection,
        stepStore.steps,
        searchStore,
    );

    // change the selection only once conversion succeeded, so a failure leaves it untouched
    keptInputSteps.forEach((stepId) => stateStore.setStepMultiSelected(stepId, false));
    expandedSelection.forEach((stepId) => stateStore.setStepMultiSelected(stepId, true));

    const stepEntriesWithFilteredInputs = removeOpenConnections(stepArray);

    const steps = Object.fromEntries(stepEntriesWithFilteredInputs.map((step) => [step.id, step]));

    const partialWorkflow: PartialWorkflow = {
        comments,
        steps,
        name,
        id: workflowId,
        annotation: "",
    };

    return {
        partialWorkflow,
        inputReconnectionMap,
        outputReconnectionMap,
        expandedSteps,
        keptInputSteps,
    };
}
