import { computed, type Ref, ref, watch } from "vue";

import { GalaxyApi, type HistoryItemSummary } from "@/api";
import { filtersToQueryValues } from "@/components/History/model/queries";
import { useHistoryStore } from "@/stores/historyStore";
import { errorMessageAsString } from "@/utils/simple-error";

const DEFAULT_FILTERS = { visible: true, deleted: false };

let singletonInstance: {
    isFetchingItems: Ref<boolean>;
    errorMessage: Ref<string | null>;
    historyItems: Ref<HistoryItemSummary[]>;
} | null = null;

/**
 * Creates a composable that fetches the given type of items from a history reactively.
 * @param historyId The history ID to fetch items for. (TODO: make this a required parameter; only `string` allowed)
 * @param type The type of items to fetch. Default is "dataset".
 * @param filters Filters to apply to the items.
 * @returns An object containing reactive properties for the fetch status and the fetched items.
 */
export function useHistoryItemsForType(
    historyId: Ref<string | null>,
    type: "dataset" | "dataset_collection" = "dataset",
    filters = DEFAULT_FILTERS
) {
    if (singletonInstance) {
        return singletonInstance;
    }
    const isFetchingItems = ref(false);
    const errorMessage = ref<string | null>(null);
    const historyItems = ref<HistoryItemSummary[]>([]);
    const counter = ref(0);

    const historyStore = useHistoryStore();

    const historyUpdateTime = computed(
        () => historyId.value && historyStore.getHistoryById(historyId.value)?.update_time
    );

    // Fetch items when history ID or update time changes
    watch(
        () => ({
            time: historyUpdateTime.value,
            id: historyId.value,
        }),
        async (newValues, oldValues) => {
            if (newValues.time !== oldValues?.time || newValues.id !== oldValues?.id) {
                await fetchItems();
                counter.value++;
            }
        },
        { immediate: true }
    );

    async function fetchItems() {
        if (!historyId.value) {
            errorMessage.value = "No history ID provided";
            return;
        }
        if (isFetchingItems.value) {
            return;
        }
        const filterQuery = filtersToQueryValues(filters);
        isFetchingItems.value = true;
        const { data, error } = await GalaxyApi().GET("/api/histories/{history_id}/contents/{type}s", {
            params: {
                path: { history_id: historyId.value, type: type },
                query: { ...filterQuery, v: "dev" },
            },
        });
        isFetchingItems.value = false;
        if (error) {
            errorMessage.value = errorMessageAsString(error);
            console.error("Error fetching history items", errorMessage.value);
        } else {
            historyItems.value = data as HistoryItemSummary[];
            errorMessage.value = null;
        }
    }

    singletonInstance = {
        isFetchingItems,
        errorMessage,
        historyItems,
    };

    return singletonInstance;
}
