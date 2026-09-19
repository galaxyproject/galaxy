import { ref } from "vue";

import type { GenericPair } from "@/components/Collections/common/buildCollectionModal";

import { autoPairWithCommonFilters, type HasName } from "./pairing";

import AutoPairing from "./common/AutoPairing.vue";

export function useAutoPairing<T extends HasName>() {
    const currentForwardFilter = ref("");
    const currentReverseFilter = ref("");
    const countPaired = ref(-1);
    const countUnpaired = ref(-1);
    const pairs = ref<GenericPair<T>[]>();
    const unpaired = ref<T[]>();

    function onFilters(forwardFilter: string, reverseFilter: string) {
        currentForwardFilter.value = forwardFilter;
        currentReverseFilter.value = reverseFilter;
    }

    function autoPair(selectedItems: T[]) {
        const thisSummary = autoPairWithCommonFilters(selectedItems, true);
        pairs.value = thisSummary.pairs;
        unpaired.value = thisSummary.unpaired;
        currentForwardFilter.value = thisSummary.forwardFilter || "";
        currentReverseFilter.value = thisSummary.reverseFilter || "";
        countPaired.value = thisSummary.pairs?.length || 0;
        countUnpaired.value = thisSummary.unpaired.length;
    }

    return {
        AutoPairing,
        autoPair,
        countPaired,
        countUnpaired,
        currentForwardFilter,
        currentReverseFilter,
        onFilters,
        pairs,
        unpaired,
    };
}
