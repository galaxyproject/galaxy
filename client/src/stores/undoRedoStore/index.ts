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

    return {
        undoActionStack,
        redoActionStack,
        maxUndoActions,
        undo,
        redo,
        applyAction,
    };
});
