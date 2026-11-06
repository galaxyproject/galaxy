let idCounter = 0;

export class UndoRedoAction {
    protected internalName?: string;
    public id: number;

    constructor() {
        this.id = idCounter++;
    }

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

    get dataAttributes(): Record<string, string> {
        return {};
    }

    /** True while an async `run` is still in progress; undo and redo wait until it finishes */
    get isPending(): boolean {
        return false;
    }
}

export class LazyUndoRedoAction extends UndoRedoAction {
    queued() {
        return;
    }
}
