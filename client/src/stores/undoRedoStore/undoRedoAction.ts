export class UndoRedoAction {
    runCallback?: () => void;
    undoCallback?: () => void;
    redoCallback?: () => void;
    destroyCallback?: () => void;

    onRun(callback: typeof this.runCallback) {
        this.runCallback = callback;
    }

    onUndo(callback: typeof this.undoCallback) {
        this.undoCallback = callback;
    }

    onRedo(callback: typeof this.redoCallback) {
        this.redoCallback = callback;
    }

    onDestroy(callback: typeof this.destroyCallback) {
        this.destroyCallback = callback;
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
