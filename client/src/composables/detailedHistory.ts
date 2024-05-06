/**
 * This module provides composable functions for working with different types (views) of history objects.
 * Containing different amounts of required information about a history object depending on the use case.
 */
import { computed, onMounted } from "vue";

import { type HistorySummaryExtended } from "@/api";
import { useHistoryStore } from "@/stores/historyStore";

/**
 * Provides the extended details for a history.
 * This composable should be used when the extended details are required.
 * The extended details usually include the size of the history and the number of active, deleted, and hidden items.
 * @param historyId The id of the history to get the extended details for.
 */
export function useExtendedHistory(historyId: string) {
    const historyStore = useHistoryStore();

    onMounted(async () => {
        // Make sure the history is loaded with the extended details
        // as it may not have been loaded yet or may not have the extended details.
        await historyStore.loadHistoryById(historyId);
    });

    const history = computed<HistorySummaryExtended>(
        () => historyStore.getHistoryById(historyId) as HistorySummaryExtended
    );

    return {
        history,
    };
}
