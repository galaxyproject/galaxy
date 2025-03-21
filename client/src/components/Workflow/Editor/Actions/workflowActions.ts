import { LazyUndoRedoAction, UndoRedoAction, type UndoRedoStore } from "@/stores/undoRedoStore";
import { useConnectionStore } from "@/stores/workflowConnectionStore";
import {
    useWorkflowCommentStore,
    type WorkflowComment,
    type WorkflowCommentStore,
} from "@/stores/workflowEditorCommentStore";
import { useWorkflowStateStore, type WorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { type Step, useWorkflowStepStore, type WorkflowStepStore } from "@/stores/workflowStepStore";
import { ensureDefined } from "@/utils/assertions";

import { type defaultPosition } from "../composables/useDefaultStepPosition";
import { fromSimple, type Workflow } from "../modules/model";
import { cloneStepWithUniqueLabel, getLabelSet } from "./cloneStep";

export class LazySetValueAction<T> extends LazyUndoRedoAction {
    setValueHandler;
    showAttributesCallback;
    fromValue;
    toValue;

    constructor(fromValue: T, toValue: T, setValueHandler: (value: T) => void, showCanvasCallback: () => void) {
        super();
        this.fromValue = structuredClone(fromValue);
        this.toValue = structuredClone(toValue);
        this.setValueHandler = setValueHandler;
        this.showAttributesCallback = showCanvasCallback;
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

    get name() {
        return this.internalName ?? "修改工作流";
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

    constructor(
        undoRedoStore: UndoRedoStore,
        setValueHandler: (value: T) => void,
        showCanvasCallback: () => void,
        name?: string
    ) {
        this.undoRedoStore = undoRedoStore;
        this.setValueHandler = setValueHandler;
        this.showAttributesCallback = showCanvasCallback;
        this.name = name;
    }

    set(from: T, to: T) {
        if (this.lazyAction && this.undoRedoStore.isQueued(this.lazyAction)) {
            this.lazyAction.changeValue(to);
        } else {
            this.lazyAction = new LazySetValueAction<T>(from, to, this.setValueHandler, this.showAttributesCallback);
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
        return `复制 ${this.data.name} 到工作流`;
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
        return "移动多个节点";
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
        if (type === "comment") {
            return `${count} ${count === 1 ? "条注释" : "条注释"}`;
        } else {
            return `${count} ${count === 1 ? "个步骤" : "个步骤"}`;
        }
    }
}

function getCombinedCountName(stepCount: number, commentCount: number) {
    const stepName = getCountName(stepCount, "step");
    const commentName = getCountName(commentCount, "comment");

    if (stepName && commentName) {
        return `${stepName} 和 ${commentName}`;
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
        return "清除选择";
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
        return `将${combinedCountName}添加到选择`;
    }
}

export class RemoveFromSelectionAction extends ModifySelectionAction {
    addToSelection = false;

    get name() {
        const combinedCountName = getCombinedCountName(this.selection.steps.length, this.selection.comments.length);
        return `从选择中移除${combinedCountName}`;
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
        return "复制选择";
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
        return "移除选择";
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
