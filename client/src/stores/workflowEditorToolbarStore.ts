import { defineStore } from "pinia";
import type { XYPosition } from "./workflowEditorStateStore";
import { computed, ref } from "vue";

export const useWorkflowEditorToolbarStore = defineStore("workflowEditorToolbarStore", () => {
    const snapDistance = 10;
    const snapActive = ref(false);

    const getSnappedPosition = computed(() => <T extends XYPosition>(position: T) => {
        if (snapActive.value) {
            return {
                ...position,
                x: Math.round(position.x / snapDistance) * snapDistance,
                y: Math.round(position.y / snapDistance) * snapDistance,
            } as T;
        } else {
            return {
                ...position,
                x: position.x,
                y: position.y,
            } as T;
        }
    });

    return {
        snapActive,
        getSnappedPosition,
    };
});
