import { toValue } from "@vueuse/core";
import { computed, type Ref } from "vue";

import type { useFilterObjectArray as UseFilterObjectArray } from "@/composables/filter";

// Use vi.mock for Vitest, jest.mock for Jest
// @ts-ignore - These are test globals
const mockFn = typeof vi !== "undefined" ? vi.mock : jest.mock;
mockFn("@/composables/filter", () => ({
    useFilterObjectArray,
}));

export const useFilterObjectArray: typeof UseFilterObjectArray = (array): Ref<any[]> => {
    return computed(() => toValue(array));
};
