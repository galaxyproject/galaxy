import { LazyUndoRedoAction, UndoRedoAction } from "@/stores/undoRedoStore";
import type {
    BaseWorkflowComment,
    WorkflowComment,
    WorkflowCommentColor,
    WorkflowCommentStore,
    WorkflowCommentType,
} from "@/stores/workflowEditorCommentStore";

function getCommentName(comment: { color: WorkflowCommentColor; type: WorkflowCommentType }) {
    if (comment.color !== "none") {
        return `${comment.color} ${comment.type} 注释`;
    } else {
        return `${comment.type} 注释`;
    }
}

class CommentAction extends UndoRedoAction {
    protected store: WorkflowCommentStore;
    protected comment: WorkflowComment;

    constructor(store: WorkflowCommentStore, comment: BaseWorkflowComment) {
        super();
        this.store = store;
        this.comment = structuredClone(comment) as WorkflowComment;
    }

    protected get commentName() {
        return getCommentName(this.comment);
    }
}

export class AddCommentAction extends CommentAction {
    get name() {
        return `添加${this.commentName}`;
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
        return `删除${this.commentName}`;
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
        return `将${this.type}注释颜色更改为${this.toColor}`;
    }

    run() {
        this.store.changeColor(this.commentId, this.toColor);
    }

    undo() {
        this.store.changeColor(this.commentId, this.fromColor);
    }
}

class LazyMutateCommentAction<K extends keyof WorkflowComment> extends LazyUndoRedoAction {
    protected commentId: number;
    protected startData: WorkflowComment[K];
    protected endData: WorkflowComment[K];
    protected type;
    protected color: WorkflowCommentColor;
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
        this.color = comment.color;
    }

    queued() {
        this.applyDataCallback(this.commentId, this.endData);
    }

    protected get commentName() {
        return getCommentName({ type: this.type, color: this.color });
    }

    get name() {
        return `更改${this.commentName}`;
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

    get name() {
        type TitleData = { title: string };
        type TextData = { text: string };
        type SizeData = { size: number };
        type FormatData = { bold?: true; italic?: true };

        if ((this.startData as TitleData).title !== (this.endData as TitleData).title) {
            return `编辑${this.commentName}的标题`;
        }

        if ((this.startData as TextData).text !== (this.endData as TextData).text) {
            return `编辑${this.commentName}的文本`;
        }

        if ((this.startData as SizeData).size !== (this.endData as SizeData).size) {
            return `更改${this.commentName}的文本大小`;
        }

        if ((this.startData as FormatData).bold !== (this.endData as FormatData).bold) {
            return `切换${this.commentName}的粗体`;
        }

        if ((this.startData as FormatData).italic !== (this.endData as FormatData).italic) {
            return `切换${this.commentName}的斜体`;
        }

        return super.name;
    }
}

export class LazyChangePositionAction extends LazyMutateCommentAction<"position"> {
    constructor(store: WorkflowCommentStore, comment: WorkflowComment, position: [number, number]) {
        const callback = store.changePosition;
        super(comment, "position", position, callback);
    }

    get name() {
        return `移动${this.commentName}`;
    }
}

export class LazyChangeSizeAction extends LazyMutateCommentAction<"size"> {
    constructor(store: WorkflowCommentStore, comment: WorkflowComment, size: [number, number]) {
        const callback = store.changeSize;
        super(comment, "size", size, callback);
    }

    get name() {
        return `调整${this.commentName}大小`;
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
            return `将${this.type}注释添加到选择`;
        } else {
            return `从选择中移除${this.type}注释`;
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
        return "移除所有手绘注释";
    }

    run() {
        this.store.deleteFreehandComments();
    }

    undo() {
        this.store.addComments(structuredClone(this.comments));
    }
}
