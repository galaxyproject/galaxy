import { defineStore } from "pinia";
import { set } from "vue";

import { type DatasetEntry, type HistoryContentItemBase } from "@/api";
import { fetchDatasetDetails } from "@/api/datasets";
import { useKeyedCache } from "@/composables/keyedCache";

export const useDatasetStore = defineStore("datasetStore", () => {
    const { storedItems, getItemById, getItemLoadError, isLoadingItem, fetchItemById } = useKeyedCache<DatasetEntry>(
        fetchDatasetDetails,
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
