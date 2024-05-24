import { defineStore } from "pinia";
import { computed, set } from "vue";

import { type DatasetDetails, type DatasetEntry, type HistoryContentItemBase, isInaccessible } from "@/api";
import { fetchDataset } from "@/api/datasets";
import { ApiResponse } from "@/api/schema";
import { useKeyedCache } from "@/composables/keyedCache";

async function fetchDatasetDetails(params: { id: string }): Promise<ApiResponse<DatasetDetails>> {
    const response = await fetchDataset({ dataset_id: params.id, view: "detailed" });
    return response as unknown as ApiResponse<DatasetDetails>;
}

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

    const { storedItems, getItemById, isLoadingItem, fetchItemById } = useKeyedCache<DatasetEntry>(
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
        isLoadingDataset: isLoadingItem,
        fetchDataset: fetchItemById,
        saveDatasets,
    };
});
