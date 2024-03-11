import { UndoRedoAction, UndoRedoStore } from "@/stores/undoRedoStore";

export class LazySetValueAction<T> extends UndoRedoAction {
    setValueHandler;
    fromValue;
    toValue;

    constructor(fromValue: T, toValue: T, setValueHandler: (value: T) => void) {
        super();
        this.fromValue = structuredClone(fromValue);
        this.toValue = structuredClone(toValue);
        this.setValueHandler = setValueHandler;
        this.setValueHandler(toValue);
    }

    changeValue(value: T) {
        this.toValue = structuredClone(value);
        this.setValueHandler(this.toValue);
    }

    undo() {
        this.setValueHandler(this.fromValue);
    }

    redo() {
        this.setValueHandler(this.toValue);
    }
}

export class SetValueActionHandler<T> {
    undoRedoStore;
    setValueHandler;
    lazyAction: LazySetValueAction<T> | null = null;

    constructor(undoRedoStore: UndoRedoStore, setValueHandler: (value: T) => void) {
        this.undoRedoStore = undoRedoStore;
        this.setValueHandler = setValueHandler;
    }

    set(from: T, to: T) {
        if (this.lazyAction && this.undoRedoStore.isQueued(this.lazyAction)) {
            this.lazyAction.changeValue(to);
        } else {
            this.lazyAction = new LazySetValueAction<T>(from, to, this.setValueHandler);
            this.undoRedoStore.applyLazyAction(this.lazyAction);
        }
    }
}
