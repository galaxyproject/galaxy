import { LazyUndoRedoAction, UndoRedoAction } from "@/stores/undoRedoStore";
import type {
    BaseWorkflowComment,
    WorkflowComment,
    WorkflowCommentColor,
    WorkflowCommentStore,
} from "@/stores/workflowEditorCommentStore";

class CommentAction extends UndoRedoAction {
    protected store: WorkflowCommentStore;
    protected comment: WorkflowComment;

    constructor(store: WorkflowCommentStore, comment: BaseWorkflowComment) {
        super();
        this.store = store;
        this.comment = structuredClone(comment) as WorkflowComment;
    }
}

export class AddCommentAction extends CommentAction {
    get name() {
        return `add ${this.comment.type} comment`;
    }

    undo() {
        this.store.deleteComment(this.comment.id);
    }

    redo() {
        this.store.addComments([this.comment]);
    }
}

export class DeleteCommentAction extends CommentAction {
    get name() {
        return `delete ${this.comment.type} comment`;
    }

    run() {
        this.store.deleteComment(this.comment.id);
    }

    undo() {
        this.store.addComments([this.comment]);
    }
}

export class ChangeColorAction extends UndoRedoAction {
    private commentId: number;
    private toColor: WorkflowCommentColor;
    private fromColor: WorkflowCommentColor;
    private store: WorkflowCommentStore;
    protected type;

    constructor(store: WorkflowCommentStore, comment: WorkflowComment, color: WorkflowCommentColor) {
        super();
        this.store = store;
        this.commentId = comment.id;
        this.fromColor = comment.color;
        this.toColor = color;
        this.type = comment.type;
    }

    get name() {
        return `change ${this.type} comment color to ${this.toColor}`;
    }

    run() {
        this.store.changeColor(this.commentId, this.toColor);
    }

    undo() {
        this.store.changeColor(this.commentId, this.fromColor);
    }
}

class LazyMutateCommentAction<K extends keyof WorkflowComment> extends LazyUndoRedoAction {
    private commentId: number;
    private startData: WorkflowComment[K];
    private endData: WorkflowComment[K];
    protected type;
    protected applyDataCallback: (commentId: number, data: WorkflowComment[K]) => void;

    constructor(
        comment: WorkflowComment,
        key: K,
        data: WorkflowComment[K],
        applyDataCallback: (commentId: number, data: WorkflowComment[K]) => void
    ) {
        super();
        this.commentId = comment.id;
        this.startData = structuredClone(comment[key]);
        this.endData = structuredClone(data);
        this.applyDataCallback = applyDataCallback;
        this.type = comment.type;
    }

    queued() {
        this.applyDataCallback(this.commentId, this.endData);
    }

    get name() {
        return `change ${this.type} comment`;
    }

    updateData(data: WorkflowComment[K]) {
        this.endData = data;
        this.applyDataCallback(this.commentId, this.endData);
    }

    redo() {
        this.applyDataCallback(this.commentId, this.endData);
    }

    undo() {
        this.applyDataCallback(this.commentId, this.startData);
    }
}

export class LazyChangeDataAction extends LazyMutateCommentAction<"data"> {
    constructor(store: WorkflowCommentStore, comment: WorkflowComment, data: WorkflowComment["data"]) {
        const callback = store.changeData;
        super(comment, "data", data, callback);
    }
}

export class LazyChangePositionAction extends LazyMutateCommentAction<"position"> {
    constructor(store: WorkflowCommentStore, comment: WorkflowComment, position: [number, number]) {
        const callback = store.changePosition;
        super(comment, "position", position, callback);
    }

    get name() {
        return `change ${this.type} comment position`;
    }
}

export class LazyChangeSizeAction extends LazyMutateCommentAction<"size"> {
    constructor(store: WorkflowCommentStore, comment: WorkflowComment, size: [number, number]) {
        const callback = store.changeSize;
        super(comment, "size", size, callback);
    }

    get name() {
        return `resize ${this.type} comment`;
    }
}

export class ToggleCommentSelectedAction extends UndoRedoAction {
    store;
    commentId;
    type;
    toggleTo: boolean;

    constructor(store: WorkflowCommentStore, comment: WorkflowComment) {
        super();

        this.store = store;
        this.commentId = comment.id;
        this.type = comment.type;
        this.toggleTo = !store.getCommentMultiSelected(this.commentId);
    }

    get name() {
        if (this.toggleTo === true) {
            return `add ${this.type} comment to selection`;
        } else {
            return `remove ${this.type} comment from selection`;
        }
    }

    run() {
        this.store.setCommentMultiSelected(this.commentId, this.toggleTo);
    }

    undo() {
        this.store.setCommentMultiSelected(this.commentId, !this.toggleTo);
    }
}

export class RemoveAllFreehandCommentsAction extends UndoRedoAction {
    store;
    comments;

    constructor(store: WorkflowCommentStore) {
        super();

        this.store = store;
        const freehandComments = store.comments.filter((comment) => comment.type === "freehand");
        this.comments = structuredClone(freehandComments);
    }

    get name() {
        return "remove all freehand comments";
    }

    run() {
        this.store.deleteFreehandComments();
    }

    undo() {
        this.store.addComments(structuredClone(this.comments));
    }
}
