export class UndoRedoAction {
    onRun?: () => void;
    onUndo?: () => void;
    onRedo?: () => void;
    onDestroy?: () => void;

    run() {
        this.onRun ? this.onRun() : null;
    }

    undo() {
        this.onUndo ? this.onUndo() : null;
    }

    redo() {
        this.onRedo ? this.onRedo() : this.run();
    }

    destroy() {
        this.onDestroy ? this.onDestroy() : null;
    }
}
