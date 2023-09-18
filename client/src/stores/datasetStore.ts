import { defineStore } from "pinia";
import Vue, { computed, ref } from "vue";

import { DatasetDetails, HistoryContentItemBase } from "./services";
import { fetchDatasetDetails } from "./services/dataset.service";

export const useDatasetStore = defineStore("datasetStore", () => {
    const storedDatasets = ref<{ [key: string]: DatasetDetails }>({});

    const getDataset = computed(() => {
        return (datasetId: string) => {
            if (!storedDatasets.value[datasetId]) {
                fetchDataset({ id: datasetId });
            }
            return storedDatasets.value[datasetId] ?? null;
        };
    });

    async function fetchDataset(params: { id: string }) {
        const dataset = await fetchDatasetDetails(params);
        Vue.set(storedDatasets.value, dataset.id, dataset);
        return dataset;
    }

    function saveDatasets(historyContentsPayload: HistoryContentItemBase[]) {
        const datasetList = historyContentsPayload
            .filter((entry) => entry.history_content_type === "dataset")
            .map((entry) => entry as DatasetDetails);
        for (const dataset of datasetList) {
            Vue.set(storedDatasets.value, dataset.id, dataset);
        }
    }

    return {
        storedDatasets,
        getDataset,
        fetchDataset,
        saveDatasets,
    };
});
