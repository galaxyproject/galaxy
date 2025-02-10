import { toValue } from "@vueuse/core";
import { computed, type Ref } from "vue";

import type { useFilterObjectArray as UseFilterObjectArray } from "@/composables/filter";

jest.mock("@/composables/filter", () => ({
    useFilterObjectArray,
}));

export const useFilterObjectArray: typeof UseFilterObjectArray = (array): Ref<any[]> => {
    console.debug("USING MOCKED useFilterObjectArray");
    return computed(() => toValue(array));
};
