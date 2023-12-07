import { defineStore } from "pinia";
import { set } from "vue";

import type { DatasetDetails, DatasetEntry, HistoryContentItemBase } from "@/api";
import { fetchDataset } from "@/api/datasets";
import { ApiResponse } from "@/api/schema";
import { useSimpleKeyStore } from "@/composables/simpleKeyStore";

async function fetchDatasetDetails(params: { id: string }): Promise<ApiResponse<DatasetDetails>> {
    const response = await fetchDataset({ dataset_id: params.id, view: "detailed" });
    return response as unknown as ApiResponse<DatasetDetails>;
}

export const useDatasetStore = defineStore("datasetStore", () => {
    const { storedItems, getItemById, isLoadingItem, fetchItemById } = useSimpleKeyStore<DatasetEntry>(
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

    function shouldFetch(dataset?: DatasetEntry) {
        if (!dataset) {
            return true;
        }
        const isNotDetailed = !("peek" in dataset);
        return isNotDetailed;
    }

    return {
        storedDatasets: storedItems,
        getDataset: getItemById,
        isLoadingDataset: isLoadingItem,
        fetchDataset: fetchItemById,
        saveDatasets,
    };
});
