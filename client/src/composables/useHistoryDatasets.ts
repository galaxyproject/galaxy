/**
 * Composable for fetching and watching history datasets based on filter criteria.
 * This encapsulates the logic for fetching datasets when history ID, update time,
 * or filter text changes, making it reusable across components like `CollectionCreatorIndex`
 * (and in the future `ChatGXY`).
 */
import { type MaybeRefOrGetter, toValue } from "@vueuse/shared";
import { computed, ref, watch } from "vue";

import { useHistoryDatasetsStore } from "@/stores/historyDatasetsStore";
import { useHistoryStore } from "@/stores/historyStore";

interface UseHistoryDatasetsOptions {
    /** The history ID to fetch datasets for */
    historyId: MaybeRefOrGetter<string>;
    /** Optional filter text to apply when fetching datasets */
    filterText?: MaybeRefOrGetter<string>;
    /** Whether fetching is enabled. When false, watchers won't trigger fetches. Defaults to `true`. */
    enabled?: MaybeRefOrGetter<boolean>;
    /** Whether to fetch immediately when the composable is initialized. Defaults to `true`. */
    immediate?: boolean;
}

export function useHistoryDatasets(options: UseHistoryDatasetsOptions) {
    const { historyId, filterText = "", enabled = true, immediate = true } = options;

    const historyStore = useHistoryStore();
    const historyDatasetsStore = useHistoryDatasetsStore();

    // Internal state
    const error = ref<string | null>(null);
    const initialFetchDone = ref(false);

    // Computed values from options
    const historyIdValue = computed(() => toValue(historyId));
    const filterTextValue = computed(() => toValue(filterText));
    const isEnabled = computed(() => toValue(enabled));

    // Get history and its update time from the history store
    const history = computed(() => historyStore.getHistoryById(historyIdValue.value));
    const historyUpdateTime = computed(() => history.value?.update_time);

    // Computed values from the store
    const isFetching = computed(() => historyDatasetsStore.isFetching[filterTextValue.value] ?? false);
    const datasets = computed(() => {
        if (historyDatasetsStore.cachedDatasetsForFilterText) {
            return historyDatasetsStore.cachedDatasetsForFilterText[filterTextValue.value] || [];
        }
        return [];
    });

    /**
     * Fetches history datasets using the current scope values.
     * Can be called manually or is triggered automatically by watchers.
     */
    async function fetchDatasets() {
        const { error: fetchError } = await historyDatasetsStore.fetchDatasetsForFiltertext(
            historyIdValue.value,
            historyUpdateTime.value,
            filterTextValue.value,
        );

        if (fetchError) {
            error.value = fetchError;
            console.error("Error fetching history datasets:", fetchError);
        } else {
            error.value = null;
        }

        if (!initialFetchDone.value) {
            initialFetchDone.value = true;
        }
    }

    // Watch for changes in scope and refetch when enabled
    watch([historyIdValue, historyUpdateTime, filterTextValue], async () => {
        if (isEnabled.value) {
            await fetchDatasets();
        }
    });

    // Watch for enabled state changes
    watch(isEnabled, async (nowEnabled) => {
        if (nowEnabled) {
            await fetchDatasets();
        }
    });

    // Initial fetch if immediate is true and enabled
    if (immediate && toValue(enabled)) {
        fetchDatasets();
    }

    return {
        /** The fetched datasets for the current filter text */
        datasets,
        /** Whether datasets are currently being fetched */
        isFetching,
        /** Any error that occurred during fetching */
        error,
        /** Whether the initial fetch has completed */
        initialFetchDone,
        /** The history object from the history store */
        history,
        /** Manually trigger a fetch */
        fetchDatasets,
    };
}
