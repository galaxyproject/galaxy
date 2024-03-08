# Undo-Redo System

The undo-redo system provides a mechanism for implementing undo/redo operations.
It is compromised of two main parts: the `UndoRedoStore`, and the `UndoRedoAction`

## Undo-Redo Store

The store handles saving and calling `UndoRedoAction`s.
It does not implement key-bindings, `undo` and `redo` still need to be called on the store.

The store is scoped, so it can be used in multiple contexts at once.
An example for this may be a tab, or pop-up having it's own separate undo-redo stack.

## Actions

How undo-redo operations are handled is determined by Undo-Redo actions.
There are two ways of creating actions:

* extending the `UndoRedoAction` class, and calling `undoRedoStore.applyAction`
* using the `undoRedoStore.action` factory

Actions always provide 4 callbacks, all of them optional:

* run / onRun: ran as soon as the action is applied to the store
* undo / onUndo: ran when an action is rolled back
* redo / onRedo: ran when an action is re-applied. If not defined, `run` will be ran instead
* destroy / onDestroy: ran when an action is discarded, either by the undo stack reaching it's max size, or if a new action is applied when this action is in the redo stack

Example: extending the `UndoRedoAction` class:

```ts
const undoRedoStore = useUndoRedoStore("some-scope");
const commentStore = useWorkflowCommentStore("some-scope");

export class DeleteCommentAction extends UndoRedoAction {
    comment: WorkflowComment;
    store: WorkflowCommentStore;

    constructor(store: WorkflowCommentStore, comment: WorkflowComment) {
        this.store = store;
        this.comment = structuredClone(this.store.commentsRecord[comment.id]!);
    }

    run() {
        this.store.deleteComment(this.comment.id);
    }

    undo() {
        this.store.addComments([this.comment]);
    }
}

undoRedoStore.applyAction(new AddCommentAction(commentStore, comment));
```

Here is the equivalent code using the inline factory:

```ts
const undoRedoStore = useUndoRedoStore("some-scope");
const commentStore = useWorkflowCommentStore("some-scope");

const newComment = structuredClone(commentStore[comment.id]!);

undoRedoStore.action()
    .onRun(() => commentStore.deleteComment(newComment.id))
    .onUndo(() => commentStore.addComments([ newComment.id ]))
    .apply();
```

Classes offer the advantage that they can be defined in another file, and easily reused, as they are self-contained.
They also make it easier to store and keep track of the state required by the action.

The inline factory is good for short, simple actions that need little to no state.
