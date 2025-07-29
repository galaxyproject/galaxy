import { nextTick, reactive } from "vue";

import { InsertStepAction } from "@/components/Workflow/Editor/Actions/stepActions";
import type {
    InputReconnectionMap,
    OutputReconnectionMap,
} from "@/components/Workflow/Editor/modules/convertOpenConnections";
import type { PartialWorkflow } from "@/components/Workflow/Editor/modules/extractSubworkflow";
import { AxisAlignedBoundingBox, type Rectangle } from "@/components/Workflow/Editor/modules/geometry";
import { getModule } from "@/components/Workflow/Editor/modules/services";
import { Services } from "@/components/Workflow/services";
import { LazyUndoRedoAction, UndoRedoAction, type UndoRedoStore } from "@/stores/undoRedoStore";
import { useConnectionStore } from "@/stores/workflowConnectionStore";
import {
    useWorkflowCommentStore,
    type WorkflowComment,
    type WorkflowCommentStore,
} from "@/stores/workflowEditorCommentStore";
import { useWorkflowStateStore, type WorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { type Step, useWorkflowStepStore, type WorkflowStepStore } from "@/stores/workflowStepStore";
import type { Connection, InputTerminal, OutputTerminal } from "@/stores/workflowStoreTypes";
import { assertDefined, ensureDefined } from "@/utils/assertions";

import type { defaultPosition } from "../composables/useDefaultStepPosition";
import { fromSimple, type Workflow } from "../modules/model";
import { cloneStepWithUniqueLabel, getLabelSet } from "./cloneStep";

export class LazySetValueAction<T> extends LazyUndoRedoAction {
    setValueHandler;
    showAttributesCallback;
    fromValue;
    toValue;
    what: string | null;

    constructor(
        fromValue: T,
        toValue: T,
        setValueHandler: (value: T) => void,
        showCanvasCallback: () => void,
        what: string | null = null
    ) {
        super();
        this.fromValue = structuredClone(fromValue);
        this.toValue = structuredClone(toValue);
        this.setValueHandler = setValueHandler;
        this.showAttributesCallback = showCanvasCallback;
        this.what = what;
    }

    queued() {
        this.setValueHandler(this.toValue);
    }

    changeValue(value: T) {
        this.toValue = structuredClone(value);
        this.setValueHandler(this.toValue);
    }

    undo() {
        this.showAttributesCallback();
        this.setValueHandler(this.fromValue);
    }

    redo() {
        this.showAttributesCallback();
        this.setValueHandler(this.toValue);
    }

    get dataAttributes(): Record<string, string> {
        if (this.what) {
            return {
                type: `set-${this.what}`,
            };
        } else {
            return {};
        }
    }

    get name() {
        return this.internalName ?? "modify workflow";
    }

    set name(name: string | undefined) {
        this.internalName = name;
    }
}

export class SetValueActionHandler<T> {
    undoRedoStore;
    setValueHandler;
    showAttributesCallback;
    lazyAction: LazySetValueAction<T> | null = null;
    name?: string;
    what: string | null;

    constructor(
        undoRedoStore: UndoRedoStore,
        setValueHandler: (value: T) => void,
        showCanvasCallback: () => void,
        name?: string,
        what: string | null = null
    ) {
        this.undoRedoStore = undoRedoStore;
        this.setValueHandler = setValueHandler;
        this.showAttributesCallback = showCanvasCallback;
        this.name = name;
        this.what = what;
    }

    set(from: T, to: T) {
        if (this.lazyAction && this.undoRedoStore.isQueued(this.lazyAction)) {
            this.lazyAction.changeValue(to);
        } else {
            this.lazyAction = new LazySetValueAction<T>(
                from,
                to,
                this.setValueHandler,
                this.showAttributesCallback,
                this.what
            );
            this.lazyAction.name = this.name;
            this.undoRedoStore.applyLazyAction(this.lazyAction);
        }
    }
}

export class CopyIntoWorkflowAction extends UndoRedoAction {
    workflowId;
    data;
    newCommentIds: number[] = [];
    newStepIds: number[] = [];
    position;
    stepStore;
    commentStore;
    subAction;
    loadWorkflowOptions: Parameters<typeof fromSimple>[2];

    constructor(
        workflowId: string,
        data: Pick<Workflow, "steps" | "comments" | "name">,
        position: ReturnType<typeof defaultPosition>
    ) {
        super();

        this.workflowId = workflowId;
        this.data = structuredClone(data);
        this.position = structuredClone(position);

        this.stepStore = useWorkflowStepStore(this.workflowId);
        this.commentStore = useWorkflowCommentStore(this.workflowId);
        const stateStore = useWorkflowStateStore(this.workflowId);

        this.subAction = new ClearSelectionAction(this.commentStore, stateStore);

        this.loadWorkflowOptions = {
            defaultPosition: this.position,
            appendData: true,
        };
    }

    get name() {
        return `Copy ${this.data.name} into workflow`;
    }

    run() {
        this.subAction.run();

        const commentIdsBefore = new Set(this.commentStore.comments.map((comment) => comment.id));
        const stepIdsBefore = new Set(Object.values(this.stepStore.steps).map((step) => step.id));

        fromSimple(this.workflowId, structuredClone(this.data), structuredClone(this.loadWorkflowOptions));

        const commentIdsAfter = this.commentStore.comments.map((comment) => comment.id);
        const stepIdsAfter = Object.values(this.stepStore.steps).map((step) => step.id);

        this.newCommentIds = commentIdsAfter.filter((id) => !commentIdsBefore.has(id));
        this.newStepIds = stepIdsAfter.filter((id) => !stepIdsBefore.has(id));
    }

    redo() {
        this.subAction.redo();

        fromSimple(this.workflowId, structuredClone(this.data), structuredClone(this.loadWorkflowOptions));
    }

    undo() {
        this.newCommentIds.forEach((id) => this.commentStore.deleteComment(id));
        this.newStepIds.forEach((id) => this.stepStore.removeStep(id));

        this.subAction.undo();
    }
}

type StepWithPosition = Step & { position: NonNullable<Step["position"]> };

export class LazyMoveMultipleAction extends LazyUndoRedoAction {
    private commentStore;
    private stepStore;
    private comments;
    private steps;

    private stepStartOffsets = new Map<number, [number, number]>();
    private commentStartOffsets = new Map<number, [number, number]>();

    private positionFrom;
    private positionTo;

    get name() {
        return "move multiple nodes";
    }

    constructor(
        commentStore: WorkflowCommentStore,
        stepStore: WorkflowStepStore,
        comments: WorkflowComment[],
        steps: StepWithPosition[],
        position: { x: number; y: number },
        positionTo?: { x: number; y: number }
    ) {
        super();
        this.commentStore = commentStore;
        this.stepStore = stepStore;
        this.comments = [...comments];
        this.steps = [...steps.map((step) => ensureDefined(stepStore.getStep(step.id)))] as StepWithPosition[];

        this.steps.forEach((step) => {
            this.stepStartOffsets.set(step.id, [step.position.left - position.x, step.position.top - position.y]);
        });

        this.comments.forEach((comment) => {
            this.commentStartOffsets.set(comment.id, [
                comment.position[0] - position.x,
                comment.position[1] - position.y,
            ]);
        });

        this.positionFrom = { ...position };
        this.positionTo = positionTo ? { ...positionTo } : { ...position };
    }

    changePosition(position: { x: number; y: number }) {
        this.setPosition(position);
        this.positionTo = { ...position };
    }

    private setPosition(position: { x: number; y: number }) {
        this.steps.forEach((step) => {
            const stepPosition = { left: 0, top: 0 };
            const offset = this.stepStartOffsets.get(step.id) ?? [0, 0];
            stepPosition.left = position.x + offset[0];
            stepPosition.top = position.y + offset[1];
            this.stepStore.updateStep({ ...step, position: stepPosition });
        });

        this.comments.forEach((comment) => {
            const offset = this.commentStartOffsets.get(comment.id) ?? [0, 0];
            const commentPosition = [position.x + offset[0], position.y + offset[1]] as [number, number];
            this.commentStore.changePosition(comment.id, commentPosition);
        });
    }

    queued() {
        this.setPosition(this.positionTo);
    }

    undo() {
        this.setPosition(this.positionFrom);
    }

    redo() {
        this.setPosition(this.positionTo);
    }
}

type SelectionState = {
    comments: number[];
    steps: number[];
};

function getCountName(count: number, type: "comment" | "step") {
    if (count === 0) {
        return null;
    } else {
        return `${count} ${count === 1 ? type : `${type}s`}`;
    }
}

function getCombinedCountName(stepCount: number, commentCount: number) {
    const stepName = getCountName(stepCount, "step");
    const commentName = getCountName(commentCount, "comment");

    if (stepName && commentName) {
        return `${stepName} and ${commentName}`;
    } else {
        return (stepName ?? commentName) as string;
    }
}

export class ClearSelectionAction extends UndoRedoAction {
    commentStore;
    stateStore;
    selectionState: SelectionState;

    constructor(commentStore: WorkflowCommentStore, stateStore: WorkflowStateStore) {
        super();

        this.commentStore = commentStore;
        this.stateStore = stateStore;

        this.selectionState = {
            comments: [...this.commentStore.multiSelectedCommentIds],
            steps: [...this.stateStore.multiSelectedStepIds],
        };
    }

    get name() {
        return "clear selection";
    }

    run() {
        this.commentStore.clearMultiSelectedComments();
        this.stateStore.clearStepMultiSelection();
    }

    undo() {
        this.selectionState.comments.forEach((id) => this.commentStore.setCommentMultiSelected(id, true));
        this.selectionState.steps.forEach((id) => this.stateStore.setStepMultiSelected(id, true));
    }
}

abstract class ModifySelectionAction extends UndoRedoAction {
    commentStore;
    stateStore;
    selection;
    abstract addToSelection: boolean;

    constructor(commentStore: WorkflowCommentStore, stateStore: WorkflowStateStore, selection: SelectionState) {
        super();

        this.commentStore = commentStore;
        this.stateStore = stateStore;
        this.selection = selection;
    }

    run() {
        this.selection.comments.forEach((id) => this.commentStore.setCommentMultiSelected(id, this.addToSelection));
        this.selection.steps.forEach((id) => this.stateStore.setStepMultiSelected(id, this.addToSelection));
    }

    undo() {
        this.selection.comments.forEach((id) => this.commentStore.setCommentMultiSelected(id, !this.addToSelection));
        this.selection.steps.forEach((id) => this.stateStore.setStepMultiSelected(id, !this.addToSelection));
    }
}

export class AddToSelectionAction extends ModifySelectionAction {
    addToSelection = true;

    get name() {
        const combinedCountName = getCombinedCountName(this.selection.steps.length, this.selection.comments.length);
        return `add ${combinedCountName} to selection`;
    }
}

export class RemoveFromSelectionAction extends ModifySelectionAction {
    addToSelection = false;

    get name() {
        const combinedCountName = getCombinedCountName(this.selection.steps.length, this.selection.comments.length);
        return `remove ${combinedCountName} from selection`;
    }
}

export class DuplicateSelectionAction extends CopyIntoWorkflowAction {
    constructor(workflowId: string) {
        const stateStore = useWorkflowStateStore(workflowId);
        const commentStore = useWorkflowCommentStore(workflowId);
        const stepStore = useWorkflowStepStore(workflowId);

        const commentIds = [...commentStore.multiSelectedCommentIds];
        const stepIds = [...stateStore.multiSelectedStepIds];

        const comments = commentIds.map((id) =>
            structuredClone(ensureDefined(commentStore.commentsRecord[id]))
        ) as WorkflowComment[];

        const labelSet = getLabelSet(stepStore);
        const steps = Object.fromEntries(
            stepIds.map((id) => [id, cloneStepWithUniqueLabel(ensureDefined(stepStore.steps[id]), labelSet)])
        );

        const partialWorkflow = { comments, steps, name: "" };

        super(workflowId, partialWorkflow, { left: 100, top: 200 });
    }

    get name() {
        return "duplicate selection";
    }
}

export class DeleteSelectionAction extends UndoRedoAction {
    storedSelectionAction: DuplicateSelectionAction;
    stateStore;
    connectionStore;
    storedConnections;

    constructor(workflowId: string) {
        super();

        this.stateStore = useWorkflowStateStore(workflowId);
        this.connectionStore = useConnectionStore(workflowId);

        this.storedSelectionAction = new DuplicateSelectionAction(workflowId);
        this.storedSelectionAction.position = { top: 0, left: 0 };
        this.storedSelectionAction.loadWorkflowOptions = {
            appendData: true,
            reassignIds: false,
            createConnections: false,
        };

        const connectionsForSteps = this.stepIds.flatMap((id) => this.connectionStore.getConnectionsForStep(id));
        this.storedConnections = structuredClone(new Set(connectionsForSteps));
    }

    get name() {
        return "delete selection";
    }

    get commentIds() {
        return this.storedSelectionAction.data.comments.map((comment) => comment.id);
    }

    get stepIds() {
        return Object.values(this.storedSelectionAction.data.steps).map((step) => step.id);
    }

    get commentStore() {
        return this.storedSelectionAction.commentStore;
    }

    get stepStore() {
        return this.storedSelectionAction.stepStore;
    }

    run() {
        this.commentIds.forEach((id) => {
            this.commentStore.deleteComment(id);
        });

        this.commentStore.clearMultiSelectedComments();

        this.stepIds.forEach((id) => {
            this.stepStore.removeStep(id);
        });

        this.stateStore.clearStepMultiSelection();
    }

    undo() {
        this.storedSelectionAction.redo();
        this.storedConnections.forEach((connection) => this.connectionStore.addConnection(structuredClone(connection)));
    }
}

export class ExtractSubworkflowAction extends UndoRedoAction {
    // hardcoded offset to improve look of final position
    subworkflowPositionOffset = {
        left: 100,
        top: 80,
    };

    deleteSelectionSubAction?: DeleteSelectionAction;
    insertSubworkflowSubAction?: InsertStepAction;

    asyncOperationDone: { value: boolean };

    services;

    stateStore;
    stepStore;
    commentStore;
    connectionStore;

    inputReconnectionMap: InputReconnectionMap;
    outputReconnectionMap: OutputReconnectionMap;
    partialWorkflow: PartialWorkflow;

    constructor(
        partialWorkflow: PartialWorkflow,
        inputReconnectionMap: InputReconnectionMap,
        outputReconnectionMap: OutputReconnectionMap
    ) {
        super();

        this.partialWorkflow = partialWorkflow;
        this.services = new Services();

        this.inputReconnectionMap = inputReconnectionMap;
        this.outputReconnectionMap = outputReconnectionMap;

        this.stateStore = useWorkflowStateStore(partialWorkflow.id);
        this.stepStore = useWorkflowStepStore(partialWorkflow.id);
        this.commentStore = useWorkflowCommentStore(partialWorkflow.id);
        this.connectionStore = useConnectionStore(partialWorkflow.id);

        this.asyncOperationDone = reactive({ value: false });
    }

    reconnect() {
        const stepId = this.insertSubworkflowSubAction?.stepId;
        const inputReconnectionMap = this.inputReconnectionMap;
        const outputReconnectionMap = this.outputReconnectionMap;

        assertDefined(stepId);
        inputReconnectionMap;
        outputReconnectionMap;

        // reconnect inputs

        const inputConnections = Object.entries(inputReconnectionMap).map(([inputName, outputLink]) => {
            const input: InputTerminal = {
                connectorType: "input",
                name: inputName,
                stepId,
            };

            const output: OutputTerminal = {
                connectorType: "output",
                name: outputLink.output_name,
                stepId: outputLink.id,
            };

            return {
                input,
                output,
            } as Connection;
        });

        inputConnections.forEach((connection) => {
            this.connectionStore.addConnection(connection);
        });

        // reconnect outputs

        const outputConnections = outputReconnectionMap.map(({ connection, name, nodeId }) => {
            const input: InputTerminal = {
                connectorType: "input",
                name,
                stepId: nodeId,
            };

            const output: OutputTerminal = {
                connectorType: "output",
                name: connection.output_name,
                stepId,
            };

            return {
                input,
                output,
            } as Connection;
        });

        outputConnections.forEach((connection) => {
            this.connectionStore.addConnection(connection);
        });
    }

    getSelectionAABB(steps: Step[], comments: WorkflowComment[]) {
        const aabb = new AxisAlignedBoundingBox();

        steps.forEach((step) => {
            const rect = this.stateStore.stepPosition[step.id];

            if (rect && step.position) {
                const stepRect: Rectangle = {
                    x: step.position.left,
                    y: step.position.top,
                    width: rect.width,
                    height: rect.height,
                };

                aabb.fitRectangle(stepRect);
            }
        });

        comments.forEach((comment) => {
            const commentRect: Rectangle = {
                x: comment.position[0],
                y: comment.position[1],
                width: comment.size[0],
                height: comment.size[1],
            };

            aabb.fitRectangle(commentRect);
        });

        return aabb;
    }

    async run() {
        const stepIds = [...this.stateStore.multiSelectedStepIds];
        const commentIds = [...this.commentStore.multiSelectedCommentIds];

        const aabb = this.getSelectionAABB(
            stepIds.map((id) => ensureDefined(this.stepStore.getStep(id))),
            commentIds.map((id) => ensureDefined(this.commentStore.commentsRecord[id]))
        );

        this.deleteSelectionSubAction = new DeleteSelectionAction(this.partialWorkflow.id);

        const newWf = await this.services.createWorkflow(this.partialWorkflow);

        this.insertSubworkflowSubAction = new InsertStepAction(this.stepStore, this.stateStore, {
            contentId: newWf.latest_workflow_id,
            name: newWf.name,
            type: "subworkflow",
            position: {
                top: aabb.y + aabb.height / 2.0 - this.subworkflowPositionOffset.top,
                left: aabb.x + aabb.width / 2.0 - this.subworkflowPositionOffset.left,
            },
        });

        this.deleteSelectionSubAction.run();
        this.insertSubworkflowSubAction.run();
        const stepData = this.insertSubworkflowSubAction.getNewStepData();

        const response = await getModule(
            { name: newWf.name, type: "subworkflow", content_id: newWf.latest_workflow_id },
            stepData.id,
            this.stateStore.setLoadingState
        );

        const updatedStep = {
            ...stepData,
            tool_state: response.tool_state,
            inputs: response.inputs,
            outputs: response.outputs,
            config_form: response.config_form,
        };

        this.stepStore.updateStep(updatedStep);
        this.insertSubworkflowSubAction.updateStepData = updatedStep;
        this.stateStore.activeNodeId = stepData.id;

        await nextTick();
        this.reconnect();

        this.asyncOperationDone.value = true;
    }

    undo() {
        assertDefined(this.insertSubworkflowSubAction);
        assertDefined(this.deleteSelectionSubAction);

        this.insertSubworkflowSubAction.undo();
        this.deleteSelectionSubAction.undo();
    }

    redo() {
        assertDefined(this.insertSubworkflowSubAction);
        assertDefined(this.deleteSelectionSubAction);

        this.insertSubworkflowSubAction.redo();
        this.deleteSelectionSubAction.redo();

        this.reconnect();
    }
}
