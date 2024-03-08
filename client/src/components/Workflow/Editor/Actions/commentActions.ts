import { UndoRedoAction } from "@/stores/undoRedoStore";
import type { BaseWorkflowComment, WorkflowCommentStore } from "@/stores/workflowEditorCommentStore";

class CommentStoreAction extends UndoRedoAction {
    store: WorkflowCommentStore;

    constructor(store: WorkflowCommentStore) {
        super();
        this.store = store;
    }
}

export class AddCommentAction extends CommentStoreAction {
    constructor(store: WorkflowCommentStore, comment: BaseWorkflowComment) {
        super(store);

        const newComment = structuredClone(this.store.commentsRecord[comment.id]!);

        this.onUndo(() => {
            this.store.deleteComment(newComment.id);
        });

        this.onRedo(() => {
            this.store.addComments([newComment]);
        });
    }
}
