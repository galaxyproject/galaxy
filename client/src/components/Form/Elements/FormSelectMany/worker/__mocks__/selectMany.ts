import { reactive, ref, watch } from "vue";

import type { SelectOption, useSelectMany as UseSelectMany } from "../selectMany";
import { main } from "../selectManyMain";

// Use vi.mock for Vitest, jest.mock for Jest
// @ts-ignore - These are test globals
const mockFn = typeof vi !== "undefined" ? vi.mock : jest.mock;
mockFn("@/components/Form/Elements/FormSelectMany/worker/selectMany", () => ({
    useSelectMany,
}));

export const useSelectMany: typeof UseSelectMany = (options) => {
    const unselectedOptionsFiltered = ref([] as SelectOption[]);
    const selectedOptionsFiltered = ref([] as SelectOption[]);
    const moreSelected = ref(false);
    const moreUnselected = ref(false);
    const running = ref(false);

    watch(
        [...Object.values(options)],
        () => {
            const result = main(reactive(options));

            unselectedOptionsFiltered.value = result.unselectedOptionsFiltered;
            selectedOptionsFiltered.value = result.selectedOptionsFiltered;
            moreSelected.value = result.moreSelected;
            moreUnselected.value = result.moreUnselected;
        },
        { immediate: true },
    );

    return {
        unselectedOptionsFiltered,
        selectedOptionsFiltered,
        moreSelected,
        moreUnselected,
        running,
    };
};
