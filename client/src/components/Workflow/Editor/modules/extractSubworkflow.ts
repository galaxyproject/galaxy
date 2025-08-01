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

    const stepIds = [...stateStore.multiSelectedStepIds];
    const commentIds = [...commentStore.multiSelectedCommentIds];

    const expandedSelection = getTraversedSelection(stepIds, stepStore.steps);
    const expandedSteps = new Set(expandedSelection).difference(new Set(stepIds));

    expandedSelection.forEach((stepId) => stateStore.setStepMultiSelected(stepId, true));

    const comments = commentIds.map((id) =>
        structuredClone(ensureDefined(commentStore.commentsRecord[id]))
    ) as WorkflowComment[];

    const { stepArray, inputReconnectionMap, outputReconnectionMap } = await convertOpenConnections(
        expandedSelection,
        stepStore.steps,
        searchStore
    );

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
    };
}
