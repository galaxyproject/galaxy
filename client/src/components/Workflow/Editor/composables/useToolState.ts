import { toRefs } from "@vueuse/core";
import { computed, type Ref } from "vue";

import { type Step } from "@/stores/workflowStepStore";

export function useToolState(step: Ref<Step>) {
    const { tool_state: rawToolStateRef } = toRefs(step);

    const toolState = computed(() => {
        const rawToolState: Record<string, unknown> = rawToolStateRef.value;
        const parsedToolState: Record<string, unknown> = {};

        // This is less than ideal in a couple ways. The fact the JSON response
        // has encoded JSON is gross and it would be great for module types that
        // do not use the tool form to just return a simple JSON blob without
        // the extra encoded. As a step two if each of these module types could
        // also define a schema so we could use typed entities shared between the
        // client and server that would be ideal.
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
