import reportDefault from "@/components/Workflow/Editor/reportDefault";
import { useWorkflowCommentStore, type WorkflowComment } from "@/stores/workflowEditorCommentStore";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { useWorkflowEditorToolbarStore } from "@/stores/workflowEditorToolbarStore";
import {
    type ConnectionOutputLink,
    type StepInputConnection,
    type Steps,
    useWorkflowStepStore,
} from "@/stores/workflowStepStore";

export interface Workflow {
    name: string;
    annotation: string;
    license: string;
    creator: any;
    version: number;
    report?: any;
    steps: Steps;
    comments: WorkflowComment[];
    tags: string[];
}

export interface LoadWorkflowOptions {
    appendData?: boolean;
    /** if set, overwrites the append data behavior of reassigning IDs */
    reassignIds?: boolean;
    createConnections?: boolean;
    defaultPosition?: { top: number; left: number };
}

/**
 * Loads a workflow into the editor
 *
 * @param id ID of workflow to load data *into*
 * @param data Workflow data to load from
 * @param appendData if true appends data to current workflow, making sure to create new uuids
 * @param defaultPosition where to position workflow in the editor
 */
export async function fromSimple(
    id: string,
    data: Pick<Workflow, "steps" | "comments" | "report">,
    options?: LoadWorkflowOptions
) {
    const appendData = options?.appendData ?? false;
    const defaultPosition = options?.defaultPosition ?? { top: 0, left: 0 };

    const commentStore = useWorkflowCommentStore(id);
    const stateStore = useWorkflowStateStore(id);
    const stepStore = useWorkflowStepStore(id);
    const toolbarStore = useWorkflowEditorToolbarStore(id);

    // If workflow being copied into another, wipe UUID and let
    // Galaxy assign new ones.
    if (options?.reassignIds ?? appendData) {
        const stepIdOffset = stepStore.getStepIndex + 1;
        const stepArray = Object.values(data.steps);

        // Since we are resigning IDs based on index, ensure correct ordering
        stepArray.sort((a, b) => a.id - b.id);

        const stepIdMapOldToNew = new Map<number, number>();

        stepArray.forEach((step, index) => {
            const oldId = step.id;
            step.id = index + stepIdOffset;
            stepIdMapOldToNew.set(oldId, step.id);
        });

        stepArray.forEach((step) => {
            delete step.uuid;
            if (!step.position) {
                // Should only happen for manually authored editor content,
                // good enough for a first pass IMO.
                step.position = { top: step.id * 100, left: step.id * 100 };
            }
            step.position.left += defaultPosition.left;
            step.position.top += defaultPosition.top;

            const newInputConnections: StepInputConnection = {};

            Object.entries(step.input_connections).forEach(([key, link]) => {
                if (link === undefined) {
                    console.error("input connections invalid", step.input_connections);
                } else {
                    let linkArray: ConnectionOutputLink[];
                    if (!Array.isArray(link)) {
                        linkArray = [link];
                    } else {
                        linkArray = link;
                    }

                    const remappedLinkArray = linkArray.map((link) => {
                        const newId = stepIdMapOldToNew.get(link.id);

                        return {
                            ...link,
                            id: newId,
                        };
                    });

                    // id may be undefined, if the partial Workflow does not contain the step
                    // in that case, remove the link
                    const newLinkArray = remappedLinkArray.filter((link) => link.id) as ConnectionOutputLink[];

                    newInputConnections[key] = newLinkArray;
                }
            });

            step.input_connections = newInputConnections;
        });

        data.comments.forEach((comment, index) => {
            comment.id = commentStore.highestCommentId + 1 + index;
        });
    }

    Object.values(data.steps).map((step) => {
        stepStore.addStep(step, appendData, options?.createConnections ?? true);
    });

    commentStore.addComments(data.comments, [defaultPosition.left, defaultPosition.top], appendData);

    if (!appendData) {
        stateStore.report = data.report ?? {
            markdown: reportDefault,
        };
    }

    toolbarStore.currentTool = "pointer";
}

export function toSimple(id: string, workflow: Workflow): Omit<Workflow, "version"> {
    const steps = workflow.steps;
    const report = workflow.report;
    const license = workflow.license;
    const creator = workflow.creator;
    const annotation = workflow.annotation;
    const name = workflow.name;
    const tags = workflow.tags;

    const commentStore = useWorkflowCommentStore(id);
    commentStore.resolveCommentsInFrames();
    commentStore.resolveStepsInFrames();

    const comments = workflow.comments.filter((comment) => !(comment.type === "text" && comment.data.text === ""));

    return { steps, report, license, creator, annotation, name, comments, tags };
}
