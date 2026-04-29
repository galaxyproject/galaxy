import { toValue } from "@vueuse/core";
import { vi } from "vitest";
import { computed, type Ref } from "vue";

import type { useFilterObjectArray as UseFilterObjectArray } from "@/composables/filter";

vi.mock("@/composables/filter", () => ({
    useFilterObjectArray,
}));

export const useFilterObjectArray: typeof UseFilterObjectArray = (array): Ref<any[]> => {
    return computed(() => toValue(array));
};
