import { LazyUndoRedoAction, UndoRedoAction, UndoRedoStore } from "@/stores/undoRedoStore";
import {
    useWorkflowCommentStore,
    type WorkflowComment,
    type WorkflowCommentStore,
} from "@/stores/workflowEditorCommentStore";
import { type Step, useWorkflowStepStore, type WorkflowStepStore } from "@/stores/workflowStepStore";

import { defaultPosition } from "../composables/useDefaultStepPosition";
import { fromSimple, Workflow } from "../modules/model";

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

    constructor(workflowId: string, data: Workflow, position: ReturnType<typeof defaultPosition>) {
        super();

        this.workflowId = workflowId;
        this.data = structuredClone(data);
        this.position = structuredClone(position);

        this.stepStore = useWorkflowStepStore(this.workflowId);
        this.commentStore = useWorkflowCommentStore(this.workflowId);
    }

    get name() {
        return `Copy ${this.data.name} into workflow`;
    }

    run() {
        const commentIdsBefore = new Set(this.commentStore.comments.map((comment) => comment.id));
        const stepIdsBefore = new Set(Object.values(this.stepStore.steps).map((step) => step.id));

        fromSimple(this.workflowId, structuredClone(this.data), {
            defaultPosition: structuredClone(this.position),
            appendData: true,
        });

        const commentIdsAfter = this.commentStore.comments.map((comment) => comment.id);
        const stepIdsAfter = Object.values(this.stepStore.steps).map((step) => step.id);

        this.newCommentIds = commentIdsAfter.filter((id) => !commentIdsBefore.has(id));
        this.newStepIds = stepIdsAfter.filter((id) => !stepIdsBefore.has(id));
    }

    redo() {
        fromSimple(this.workflowId, structuredClone(this.data), {
            defaultPosition: structuredClone(this.position),
            appendData: true,
        });
    }

    undo() {
        this.newCommentIds.forEach((id) => this.commentStore.deleteComment(id));
        this.newStepIds.forEach((id) => this.stepStore.removeStep(id));
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
        this.steps = [...steps];

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
