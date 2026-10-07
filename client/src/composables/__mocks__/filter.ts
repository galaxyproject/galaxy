import { toValue } from "@vueuse/core";
import { vi } from "vitest";
import { computed, ref } from "vue";

import type { useFilterObjectArray as UseFilterObjectArray } from "@/composables/filter";

vi.mock("@/composables/filter", () => ({
    useFilterObjectArray,
}));

export const useFilterObjectArray = ((array) => {
    return { filtered: computed(() => toValue(array)), pending: ref(false) };
}) as typeof UseFilterObjectArray;
