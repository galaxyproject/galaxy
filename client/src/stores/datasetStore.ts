import { defineStore } from "pinia";
import { computed, set } from "vue";

import { type DatasetEntry, type HistoryContentItemBase, isInaccessible } from "@/api";
import { fetchDatasetDetails } from "@/api/datasets";
import { useKeyedCache } from "@/composables/keyedCache";

export const useDatasetStore = defineStore("datasetStore", () => {
    const shouldFetch = computed(() => {
        return (dataset?: DatasetEntry) => {
            if (!dataset) {
                return true;
            }
            if (isInaccessible(dataset)) {
                return false;
            }
            const isNotDetailed = !("peek" in dataset);
            return isNotDetailed;
        };
    });

    const { storedItems, getItemById, getItemLoadError, isLoadingItem, fetchItemById } = useKeyedCache<DatasetEntry>(
        fetchDatasetDetails,
        shouldFetch
    );

    function saveDatasets(historyContentsPayload: HistoryContentItemBase[]) {
        const datasetList = historyContentsPayload.filter(
            (entry) => entry.history_content_type === "dataset"
        ) as DatasetEntry[];
        for (const dataset of datasetList) {
            set(storedItems.value, dataset.id, dataset);
        }
    }

    return {
        storedDatasets: storedItems,
        getDataset: getItemById,
        getDatasetError: getItemLoadError,
        isLoadingDataset: isLoadingItem,
        fetchDataset: fetchItemById,
        saveDatasets,
    };
});
