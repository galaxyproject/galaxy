import { UndoRedoAction } from "@/stores/undoRedoStore";
import type { BaseWorkflowComment, WorkflowComment, WorkflowCommentStore } from "@/stores/workflowEditorCommentStore";

class CommentStoreAction extends UndoRedoAction {
    store: WorkflowCommentStore;

    constructor(store: WorkflowCommentStore) {
        super();
        this.store = store;
    }
}

export class AddCommentAction extends CommentStoreAction {
    comment: WorkflowComment;

    constructor(store: WorkflowCommentStore, comment: BaseWorkflowComment) {
        super(store);
        this.comment = structuredClone(this.store.commentsRecord[comment.id]!);
    }

    undo() {
        this.store.deleteComment(this.comment.id);
    }

    redo() {
        this.store.addComments([this.comment]);
    }
}

export class DeleteCommentAction extends CommentStoreAction {
    comment: WorkflowComment;

    constructor(store: WorkflowCommentStore, comment: WorkflowComment) {
        super(store);
        this.comment = structuredClone(this.store.commentsRecord[comment.id]!);
    }

    run() {
        this.store.deleteComment(this.comment.id);
    }

    undo() {
        this.store.addComments([this.comment]);
    }
}
