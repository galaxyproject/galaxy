import { toValue } from "@vueuse/core";
import { computed, type Ref } from "vue";

import type { useFilterObjectArray as UseFilterObjectArray } from "@/composables/filter";

// Use vi.mock for Vitest, jest.mock for Jest
// @ts-ignore - These are test globals
if (typeof vi !== "undefined") {
    // Vitest
    // @ts-ignore - vi is a Vitest global
    vi.mock("@/composables/filter", () => ({
        useFilterObjectArray,
    }));
} else {
    // Jest
    // @ts-ignore - jest is a Jest global
    jest.mock("@/composables/filter", () => ({
        useFilterObjectArray,
    }));
}

export const useFilterObjectArray: typeof UseFilterObjectArray = (array): Ref<any[]> => {
    return computed(() => toValue(array));
};
