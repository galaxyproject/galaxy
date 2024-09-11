import { type Ref, ref, watch } from "vue";

import { assertDefined } from "@/utils/assertions";

import { type SelectOption } from "./worker/selectMany";

/**
 * Handles logic required for highlighting options
 * @param options Array of select options to handle highlighting for
 */
export function useHighlight(options: Ref<SelectOption[]>) {
    const highlightedOptions = ref<SelectOption[]>([]);
    const highlightedIndexes = ref<number[]>([]);

    const reset = () => {
        highlightedOptions.value = [];
        highlightedIndexes.value = [];
        abortHighlight();
    };

    watch(
        () => options.value,
        () => reset()
    );

    let highlightIndexStart = -1;

    const rangeHighlight = (index: number) => {
        if (highlightIndexStart === -1) {
            highlightIndexStart = index;
            addHighlight(index);
            return;
        }

        const from = Math.min(highlightIndexStart, index);
        const to = Math.max(highlightIndexStart, index);

        for (let i = from; i <= to; i++) {
            addHighlight(i);
        }

        highlightIndexStart = -1;
    };

    const rangeRemoveHighlight = (index: number) => {
        if (highlightIndexStart === -1) {
            highlightIndexStart = index;
            removeHighlight(index);
            return;
        }

        const from = Math.min(highlightIndexStart, index);
        const to = Math.max(highlightIndexStart, index);

        for (let i = from; i <= to; i++) {
            removeHighlight(i);
        }

        highlightIndexStart = -1;
    };

    const removeHighlight = (index: number) => {
        const position = highlightedIndexes.value.indexOf(index);

        if (position !== -1) {
            highlightedIndexes.value.splice(position, 1);
            highlightedOptions.value.splice(position, 1);
        }
    };

    const addHighlight = (index: number) => {
        const position = highlightedIndexes.value.indexOf(index);

        if (position === -1) {
            highlightedIndexes.value.push(index);
            const option = options.value[index];
            assertDefined(option);
            highlightedOptions.value.push(option);
        }
    };

    const toggleHighlight = (index: number) => {
        const position = highlightedIndexes.value.indexOf(index);

        if (position === -1) {
            highlightedIndexes.value.push(index);
            const option = options.value[index];
            assertDefined(option);
            highlightedOptions.value.push(option);
        } else {
            highlightedIndexes.value.splice(position, 1);
            highlightedOptions.value.splice(position, 1);
        }
    };

    const abortHighlight = () => {
        highlightIndexStart = -1;
    };

    return {
        highlightedOptions,
        highlightedIndexes,
        reset,
        rangeHighlight,
        rangeRemoveHighlight,
        toggleHighlight,
        abortHighlight,
        addHighlight,
        removeHighlight,
    };
}
