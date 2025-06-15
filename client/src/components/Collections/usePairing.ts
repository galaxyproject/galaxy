import { ref } from "vue";

import { autoPairWithCommonFilters, type HasName } from "./pairing";

import AutoPairing from "./common/AutoPairing.vue";

export function useAutoPairing() {
    const currentForwardFilter = ref("");
    const currentReverseFilter = ref("");
    const countPaired = ref(-1);
    const countUnpaired = ref(-1);

    function onFilters(forwardFilter: string, reverseFilter: string) {
        currentForwardFilter.value = forwardFilter;
        currentReverseFilter.value = reverseFilter;
    }

    function autoPair(selectedItems: HasName[]) {
        const summary = autoPairWithCommonFilters(selectedItems, true);
        currentForwardFilter.value = summary.forwardFilter || "";
        currentReverseFilter.value = summary.reverseFilter || "";
        countPaired.value = summary.pairs?.length || 0;
        countUnpaired.value = summary.unpaired.length;
    }

    return {
        AutoPairing,
        autoPair,
        countPaired,
        countUnpaired,
        currentForwardFilter,
        currentReverseFilter,
        onFilters,
    };
}
