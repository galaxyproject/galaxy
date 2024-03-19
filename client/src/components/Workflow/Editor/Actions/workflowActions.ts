import { UndoRedoAction, UndoRedoStore } from "@/stores/undoRedoStore";

export class LazySetValueAction<T> extends UndoRedoAction {
    setValueHandler;
    showAttributesCallback;
    fromValue;
    toValue;

    constructor(fromValue: T, toValue: T, setValueHandler: (value: T) => void, showCanvasCallback: () => void) {
        super();
        this.fromValue = structuredClone(fromValue);
        this.toValue = structuredClone(toValue);
        this.setValueHandler = setValueHandler;
        this.showAttributesCallback = showCanvasCallback;

        this.setValueHandler(toValue);
    }

    changeValue(value: T) {
        this.toValue = structuredClone(value);
        this.setValueHandler(this.toValue);
    }

    undo() {
        this.showAttributesCallback();
        this.setValueHandler(this.fromValue);
    }

    redo() {
        this.showAttributesCallback();
        this.setValueHandler(this.toValue);
    }

    get name() {
        return this.internalName ?? "modify workflow";
    }

    set name(name: string | undefined) {
        this.internalName = name;
    }
}

export class SetValueActionHandler<T> {
    undoRedoStore;
    setValueHandler;
    showAttributesCallback;
    lazyAction: LazySetValueAction<T> | null = null;
    name?: string;

    constructor(
        undoRedoStore: UndoRedoStore,
        setValueHandler: (value: T) => void,
        showCanvasCallback: () => void,
        name?: string
    ) {
        this.undoRedoStore = undoRedoStore;
        this.setValueHandler = setValueHandler;
        this.showAttributesCallback = showCanvasCallback;
        this.name = name;
    }

    set(from: T, to: T) {
        if (this.lazyAction && this.undoRedoStore.isQueued(this.lazyAction)) {
            this.lazyAction.changeValue(to);
        } else {
            this.lazyAction = new LazySetValueAction<T>(from, to, this.setValueHandler, this.showAttributesCallback);
            this.lazyAction.name = this.name;
            this.undoRedoStore.applyLazyAction(this.lazyAction);
        }
    }
}
