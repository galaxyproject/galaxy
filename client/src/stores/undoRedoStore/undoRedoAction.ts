export class UndoRedoAction {
    private internalName?: string;

    get name(): string | undefined {
        return this.internalName;
    }

    set name(name: string) {
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
