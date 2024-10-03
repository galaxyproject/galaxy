import { toValue } from "@vueuse/core";
import { Ref, ref } from "vue";

import type { useFilterObjectArray as UseFilterObjectArray } from "@/composables/filter";

jest.mock("@/composables/filter", () => ({
    useFilterObjectArray,
}));

export const useFilterObjectArray: typeof UseFilterObjectArray = (array): Ref<any[]> => {
    console.debug("USING MOCKED useFilterObjectArray");
    return ref(toValue(array));
};
