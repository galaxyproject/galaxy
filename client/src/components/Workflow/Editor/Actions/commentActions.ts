import { UndoRedoAction } from "@/stores/undoRedoStore";
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
        this.comment = structuredClone(this.store.commentsRecord[comment.id]!);
    }
}

export class AddCommentAction extends CommentAction {
    undo() {
        this.store.deleteComment(this.comment.id);
    }

    redo() {
        this.store.addComments([this.comment]);
    }
}

export class DeleteCommentAction extends CommentAction {
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

    constructor(store: WorkflowCommentStore, comment: WorkflowComment, color: WorkflowCommentColor) {
        super();
        this.store = store;
        this.commentId = comment.id;
        this.fromColor = comment.color;
        this.toColor = color;
    }

    run() {
        this.store.changeColor(this.commentId, this.toColor);
    }

    undo() {
        this.store.changeColor(this.commentId, this.fromColor);
    }
}

class MutateCommentAction<K extends keyof WorkflowComment> extends UndoRedoAction {
    private commentId: number;
    private startData: WorkflowComment[K];
    private endData: WorkflowComment[K];
    private ran = false;
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
        this.applyDataCallback(this.commentId, this.endData);
    }

    updateData(data: WorkflowComment[K]) {
        if (this.ran) {
            throw new Error("data of a mutation action can not be changed once the action was run");
        } else {
            this.endData = data;
            this.applyDataCallback(this.commentId, this.endData);
        }
    }

    run() {
        this.applyDataCallback(this.commentId, this.endData);
        this.ran = true;
    }

    undo() {
        this.applyDataCallback(this.commentId, this.startData);
    }
}

export class ChangeDataAction extends MutateCommentAction<"data"> {
    constructor(store: WorkflowCommentStore, comment: WorkflowComment, data: WorkflowComment["data"]) {
        const callback = store.changeData;
        super(comment, "data", data, callback);
    }
}

export class ChangePositionAction extends MutateCommentAction<"position"> {
    constructor(store: WorkflowCommentStore, comment: WorkflowComment, position: [number, number]) {
        const callback = store.changePosition;
        super(comment, "position", position, callback);
    }
}

export class ChangeSizeAction extends MutateCommentAction<"size"> {
    constructor(store: WorkflowCommentStore, comment: WorkflowComment, size: [number, number]) {
        const callback = store.changeSize;
        super(comment, "size", size, callback);
    }
}
