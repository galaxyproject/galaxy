import { UndoRedoAction, UndoRedoStore } from "@/stores/undoRedoStore";
import { LazyUndoRedoAction } from "@/stores/undoRedoStore/undoRedoAction";
import { useWorkflowCommentStore } from "@/stores/workflowEditorCommentStore";
import { useWorkflowStepStore } from "@/stores/workflowStepStore";

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

        fromSimple(this.workflowId, structuredClone(this.data), true, structuredClone(this.position));

        const commentIdsAfter = this.commentStore.comments.map((comment) => comment.id);
        const stepIdsAfter = Object.values(this.stepStore.steps).map((step) => step.id);

        this.newCommentIds = commentIdsAfter.filter((id) => !commentIdsBefore.has(id));
        this.newStepIds = stepIdsAfter.filter((id) => !stepIdsBefore.has(id));
    }

    redo() {
        fromSimple(this.workflowId, structuredClone(this.data), true, structuredClone(this.position));
    }

    undo() {
        this.newCommentIds.forEach((id) => this.commentStore.deleteComment(id));
        this.newStepIds.forEach((id) => this.stepStore.removeStep(id));
    }
}
