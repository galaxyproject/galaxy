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
}

export class LazyUndoRedoAction extends UndoRedoAction {
    queued() {
        return;
    }
}
