import { computed, ref } from "vue";

import { type AutoPairingResult, type HasName, splitIntoPairedAndUnpaired } from "@/components/Collections/pairing";

import type { SupportedPairedOrPairedBuilderCollectionTypes } from "./useCollectionCreator";

interface PropsWithCollectionType {
    collectionType: SupportedPairedOrPairedBuilderCollectionTypes;
}

export function usePairingSummary<T extends HasName>(props: PropsWithCollectionType) {
    const currentSummary = ref<AutoPairingResult<T>>();

    const summaryText = computed(() => {
        const summary = currentSummary.value;
        if (summary) {
            const numMatchedText = `Auto-matched ${summary.pairs.length} pair(s) of datasets from target datasets.`;
            const numUnmatched = summary.unpaired.length;
            let numUnmatchedText = "";
            if (numUnmatched > 0 && props.collectionType.endsWith(":paired")) {
                numUnmatchedText = `${numUnmatched} dataset(s) were not paired and will not be included in the resulting list of pairs.`;
            } else if (numUnmatched > 0) {
                numUnmatchedText = `${numUnmatched} dataset(s) were not paired and will be included in the resulting list as unpaired datasets.`;
            }
            return `${numMatchedText} ${numUnmatchedText}`;
        } else {
            return "Auto-pairing...";
        }
    });

    function autoPair(elements: T[], forwardFilter: string, reverseFilter: string, willRemoveExtensions: boolean) {
        const summary = splitIntoPairedAndUnpaired(elements, forwardFilter, reverseFilter, willRemoveExtensions);
        currentSummary.value = summary;
    }

    return {
        currentSummary,
        summaryText,
        autoPair,
    };
}
