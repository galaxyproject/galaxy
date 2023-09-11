import { defineStore } from "pinia";
import { ref } from "vue";

import { useUserLocalStorage } from "@/composables/userLocalStorage";

export type CommentTool = "textComment" | "markdownComment" | "frameComment" | "freehandComment" | "freehandEraser";
export type EditorTool = "pointer" | CommentTool;

export type WorkflowEditorToolbarStore = ReturnType<typeof useWorkflowEditorToolbarStore>;

export const useWorkflowEditorToolbarStore = (workflowId: string) => {
    return defineStore(`workflowEditorToolbarStore${workflowId}`, () => {
        const snapActive = useUserLocalStorage("workflow-editor-toolbar-snap-active", false);
        const currentTool = ref<EditorTool>("pointer");
        const snapDistance = ref<10 | 20 | 50 | 100 | 200>(10);

        return {
            snapActive,
            snapDistance,
            currentTool,
        };
    })();
};
