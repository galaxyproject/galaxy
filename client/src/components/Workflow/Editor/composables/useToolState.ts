import { toRefs } from "@vueuse/core";
import { computed, type Ref } from "vue";

import { type Step } from "@/stores/workflowStepStore";

export function useToolState(step: Ref<Step>) {
    const { tool_state: rawToolStateRef } = toRefs(step);

    const toolState = computed(() => {
        const rawToolState: Record<string, unknown> = rawToolStateRef.value;
        const parsedToolState: Record<string, unknown> = {};

        for (const key in rawToolState) {
            if (Object.prototype.hasOwnProperty.call(rawToolState, key)) {
                const value = rawToolState[key];
                if (typeof value === "string") {
                    try {
                        const parsedValue = JSON.parse(value);
                        parsedToolState[key] = parsedValue;
                    } catch (error) {
                        parsedToolState[key] = rawToolState[key];
                    }
                } else {
                    parsedToolState[key] = rawToolState[key];
                }
            }
        }
        return parsedToolState;
    });

    return {
        toolState,
    };
}
