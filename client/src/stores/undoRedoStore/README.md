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
There are two ways of defining actions:

-   extending the `UndoRedoAction`/`LazyUndoRedoAction` class
-   using the `undoRedoStore.action` factory

The base `UndoRedoAction` class provides 5 methods which can be overridden, all of them optional:

-   run / onRun: ran as soon as the action is committed to the undo stack
-   undo / onUndo: ran when an action is rolled back
-   redo / onRedo: ran when an action is re-applied. If not defined, `run` will be ran instead
-   destroy / onDestroy: ran when an action is discarded, either by the undo stack reaching it's max size, or if a new action is applied when this action is in the redo stack
-   get name / setName: determines the actions name in the user interface

Additionally, lazy actions provide the following method:

-   queued: ran when `applyLazyAction` is called on the store

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

    get name() {
        return `delete ${this.comment.type} comment`;
    }
}

undoRedoStore.applyAction(new AddCommentAction(commentStore, comment));
```

Here is the equivalent code using the inline factory:

```ts
const undoRedoStore = useUndoRedoStore("some-scope");
const commentStore = useWorkflowCommentStore("some-scope");

const newComment = structuredClone(commentStore[comment.id]!);

undoRedoStore
    .action()
    .onRun(() => commentStore.deleteComment(newComment.id))
    .onUndo(() => commentStore.addComments([newComment.id]))
    .setName(() => `delete ${newComment.type} comment`)
    .apply();
```

Classes offer the advantage that they can be defined in another file and easily reused, as they are self-contained.
They also make it easier to store and keep track of the state required by the action.

The inline factory is good for short, simple actions that need little to no state.

## Lazy Actions

Sometimes many similar events happen in a short time frame, and we do not want to save them all as individual actions.
One example for this may be entering text. Having every individual letter as an undo action is not practical.

This is where lazy actions come in. They can be applied, by calling `undoRedoStore.applyLazyAction`.

When calling this function, the committing of the action to the undo stack is delayed, and as long as it hasn't entered the undo stack, we can mutate the action.

In order to check if an action is still waiting to be applied, we can use `undoRedoStore.isQueued`.
As long as this check returns true, it is save to mutate the action.

Applying any action, or applying a new lazy action, will apply the currently pending action and push it to the undo stack.
Lazy actions can also be ran immediately, canceled, or have their time delay extended.

A lazy actions `queued` method is ran as soon as `applyLazyAction` is called, and it's `run` method once it gets committed to the store.

Due to the additional complexity introduced by mutating action state, it is not recommended to use lazy actions together with the factory api.

Here is an example of a lazy action in action.

```ts
class ChangeCommentPositionAction extends UndoRedoAction {
    private store: WorkflowCommentStore;
    private commentId: number;
    private startPosition: Position;
    private endPosition: Position;

    constructor(store: WorkflowCommentStore, comment: WorkflowComment, position: Position) {
        super();
        this.store;
        this.commentId = comment.id;
        this.startPosition = structuredClone(position);
        this.endPosition = structuredClone(position);
        this.store.changePosition(this.commentId, position);
    }

    updatePosition(position: Position) {
        this.endPosition = position;
        this.store.changePosition(this.commentId, position);
    }

    redo() {
        this.store.changePosition(this.commentId, this.endPosition);
    }

    undo() {
        this.store.changePosition(this.commentId, this.startPosition);
    }
}
```

In this example, we would call `updatePosition` as long as the action hasn't been applied to the undo stack.

```ts
let lazyAction: ChangeCommentPositionAction | null = null;

function onCommentChangePosition(position: Position) {
    if (lazyAction && undoRedoStore.isQueued(lazyAction)) {
        lazyAction.updatePosition(position);
    } else {
        lazyAction = new ChangeCommentPositionAction(commentStore, comment, position);
        undoRedoStore.applyLazyAction(lazyAction);
    }
}
```

## Tips and Tricks

**Do not rely on data which may be deleted by an Action**

For example, relying on a vue component instance, or any object instance for that matter, may break if the object gets deleted and re-created.

Instead treat all data as if it were serializable.

**Operate on stores as much as you can**

The safest thing to mutate from an Undo-Redo Action is a store, since they are singletons by nature,
and you can be fairly certain that they will be around as long as your UndoRedoStore instance will be.

**Use shallow and deep copies to avoid state mutation**

Accidentally mutating the state of an action once it is applies breaks the undo-redo stack.
Undoing or Redoing an action may now no longer yield the same results.

Using shallow copies (`{ ...object }; [ ...array ];`) or deep copies (`structuredClone(object)`),
avoids accidental mutation.

**Write tests**

To make sure that your action is bi-directional, write a test applying, undoing, and redoing the action, comparing state-snapshots in-between. Look at the Workflow Editor actions for an example of this.
