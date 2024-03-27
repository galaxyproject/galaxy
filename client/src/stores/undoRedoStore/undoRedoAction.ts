export class UndoRedoAction {
    protected internalName?: string;

    get name(): string | undefined {
        return this.internalName;
    }

    set name(name: string | undefined) {
        this.internalName = name;
    }

    run() {
        return;
    }

    undo() {
        return;
    }

    redo() {
        this.run();
    }

    destroy() {
        return;
    }
}

export class LazyUndoRedoAction extends UndoRedoAction {
    queued() {
        return;
    }
}
