import { useLocalStorage } from "@vueuse/core";
import { defineStore } from "pinia";
import { computed, del, ref, set } from "vue";

import { ensureDefined } from "@/utils/assertions";
import { getShortToolId } from "@/utils/tool";
import { match } from "@/utils/utils";

import type { Step } from "./workflowStepStore";

interface StoredSize {
    width: number;
    maximized: boolean;
}

function getContentId(step: Step) {
    return match(step.type, {
        tool: () => `tool_${getShortToolId(ensureDefined(step.content_id))}`,
        subworkflow: () => `subworkflow_${step.content_id}`,
        data_collection_input: () => "input",
        data_input: () => "input",
        parameter_input: () => "input",
        pause: () => "pause",
    });
}

export const useWorkflowNodeInspectorStore = defineStore("workflowNodeInspectorStore", () => {
    /** width of the node inspector if no other width is stored */
    const generalWidth = useLocalStorage("workflowNodeInspectorGeneralWidth", 300);
    /** maximized state of the node inspector if no other value is stored */
    const generalMaximized = ref(false);
    const storedSizes = useLocalStorage<Record<string, StoredSize>>("workflowNodeInspectorStoredSizes", {});

    const isStored = computed(() => (step: Step) => {
        const id = getContentId(step);
        const storedIds = new Set(Object.keys(storedSizes.value));

        return storedIds.has(id);
    });

    function setStored(step: Step, stored: boolean) {
        const id = getContentId(step);
        const storedValue = storedSizes.value[id];

        if (stored) {
            if (!storedValue) {
                set(storedSizes.value, id, {
                    width: generalWidth.value,
                    maximized: generalMaximized.value,
                });
            }
        } else {
            if (storedValue) {
                generalWidth.value = storedValue.width;
                generalMaximized.value = storedValue.maximized;
                del(storedSizes.value, id);
            }
        }
    }

    const width = computed(() => (step: Step) => {
        const id = getContentId(step);
        return storedSizes.value[id]?.width ?? generalWidth.value;
    });

    /**
     * sets the inspectors width. If the width is stored,
     * stores the new width, otherwise, updates the general width
     */
    function setWidth(step: Step, newWidth: number) {
        const id = getContentId(step);

        if (storedSizes.value[id]) {
            storedSizes.value[id]!.width = newWidth;
        } else {
            generalWidth.value = newWidth;
        }
    }

    const maximized = computed(() => (step: Step) => {
        const id = getContentId(step);
        return storedSizes.value[id]?.maximized ?? generalMaximized.value;
    });

    /**
     * sets the inspectors maximized state. If the state is stored,
     * stores the maximized state, otherwise, updates the general maximized state
     */
    function setMaximized(step: Step, newMaximized: boolean) {
        const id = getContentId(step);

        if (storedSizes.value[id]) {
            storedSizes.value[id]!.maximized = newMaximized;
        } else {
            generalMaximized.value = newMaximized;
        }
    }

    function clearAllStored() {
        storedSizes.value = {};
    }

    return {
        isStored,
        setStored,
        clearAllStored,
        generalWidth,
        generalMaximized,
        width,
        setWidth,
        maximized,
        setMaximized,
    };
});
