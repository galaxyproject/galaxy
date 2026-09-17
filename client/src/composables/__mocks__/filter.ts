import { toValue } from "@vueuse/core";
import { computed, ref } from "vue";

import type { useFilterObjectArray as UseFilterObjectArray } from "@/composables/filter";

// @ts-ignore - vi is a Vitest global
vi.mock("@/composables/filter", () => ({
    useFilterObjectArray,
}));

export const useFilterObjectArray = ((array) => {
    return { filtered: computed(() => toValue(array)), pending: ref(false) };
}) as typeof UseFilterObjectArray;
