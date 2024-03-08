import { ref } from "vue";

import { defineScopedStore } from "@/stores/scopedStore";

import { UndoRedoAction } from "./undoRedoAction";

export { UndoRedoAction } from "./undoRedoAction";

export type UndoRedoStore = ReturnType<typeof useUndoRedoStore>;

export const useUndoRedoStore = defineScopedStore("undoRedoStore", () => {
    const undoActionStack = ref<UndoRedoAction[]>([]);
    const redoActionStack = ref<UndoRedoAction[]>([]);
    const maxUndoActions = ref(100);

    function undo() {
        const action = undoActionStack.value.pop();

        if (action !== undefined) {
            action.undo();
            redoActionStack.value.push(action);
        }
    }

    function redo() {
        const action = redoActionStack.value.pop();

        if (action !== undefined) {
            action.redo();
            undoActionStack.value.push(action);
        }
    }

    function applyAction(action: UndoRedoAction) {
        action.run();
        clearRedoStack();
        undoActionStack.value.push(action);

        while (undoActionStack.value.length > maxUndoActions.value && undoActionStack.value.length > 0) {
            const action = undoActionStack.value.shift();
            action?.destroy();
        }
    }

    function clearRedoStack() {
        redoActionStack.value.forEach((action) => action.destroy());
        redoActionStack.value = [];
    }

    /**
     * constructs a new action inline
     *
     * @example
     * action()
     *     .onRun(() => console.log("run"))
     *     .onUndo(() => console.log("undo"))
     *     .apply();
     */
    function action() {
        return new FactoryAction((action) => applyAction(action));
    }

    return {
        undoActionStack,
        redoActionStack,
        maxUndoActions,
        undo,
        redo,
        applyAction,
        action,
    };
});

class FactoryAction extends UndoRedoAction {
    private applyCallback: (action: FactoryAction) => void;

    private runCallback?: () => void;
    private undoCallback?: () => void;
    private redoCallback?: () => void;
    private destroyCallback?: () => void;

    constructor(applyCallback: (action: FactoryAction) => void) {
        super();
        this.applyCallback = applyCallback;
    }

    onRun(callback: typeof this.runCallback) {
        this.runCallback = callback;
        return this;
    }

    onUndo(callback: typeof this.undoCallback) {
        this.undoCallback = callback;
        return this;
    }

    onRedo(callback: typeof this.redoCallback) {
        this.redoCallback = callback;
        return this;
    }

    onDestroy(callback: typeof this.destroyCallback) {
        this.destroyCallback = callback;
        return this;
    }

    apply() {
        this.applyCallback(this);
    }

    run() {
        this.runCallback ? this.runCallback() : null;
    }

    undo() {
        this.undoCallback ? this.undoCallback() : null;
    }

    redo() {
        this.redoCallback ? this.redoCallback() : this.run();
    }

    destroy() {
        this.destroyCallback ? this.destroyCallback() : null;
    }
}
