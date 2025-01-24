import { computed, type Ref } from "vue";

import { type HistoryContentsStats } from "@/api";

export function useHistoryContentStats(history: Ref<HistoryContentsStats>) {
    const historySize = computed(() => history.value?.size ?? 0);
    const numItemsActive = computed(() => history.value?.contents_active?.active ?? 0);
    const numItemsDeleted = computed(() => history.value?.contents_active?.deleted ?? 0);
    const numItemsHidden = computed(() => history.value?.contents_active?.hidden ?? 0);

    return {
        historySize,
        numItemsActive,
        numItemsDeleted,
        numItemsHidden,
    };
}
