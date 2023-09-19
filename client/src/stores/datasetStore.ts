import { defineStore } from "pinia";
import Vue, { computed, ref } from "vue";

import { DatasetDetails, DatasetEntry, HistoryContentItemBase } from "./services";
import { fetchDatasetDetails } from "./services/dataset.service";

export const useDatasetStore = defineStore("datasetStore", () => {
    const storedDatasets = ref<{ [key: string]: DatasetDetails }>({});
    const loadingDatasets = ref<{ [key: string]: boolean }>({});

    const getDataset = computed(() => {
        return (datasetId: string) => {
            const dataset = storedDatasets.value[datasetId];
            if (needsUpdate(dataset)) {
                fetchDataset({ id: datasetId });
            }
            return dataset ?? null;
        };
    });

    const isLoadingDataset = computed(() => {
        return (datasetId: string) => {
            return loadingDatasets.value[datasetId] ?? false;
        };
    });

    async function fetchDataset(params: { id: string }) {
        loadingDatasets.value[params.id] = true;
        const dataset = await fetchDatasetDetails(params);
        Vue.set(storedDatasets.value, dataset.id, dataset);
        delete loadingDatasets.value[params.id];
        return dataset;
    }

    function saveDatasets(historyContentsPayload: HistoryContentItemBase[]) {
        const datasetList = historyContentsPayload.filter(
            (entry) => entry.history_content_type === "dataset"
        ) as DatasetEntry[];
        for (const dataset of datasetList) {
            Vue.set(storedDatasets.value, dataset.id, dataset);
        }
    }

    function needsUpdate(dataset?: DatasetEntry) {
        if (!dataset) {
            return true;
        }
        const isNotDetailed = !("peek" in dataset);
        return isNotDetailed;
    }

    return {
        storedDatasets,
        getDataset,
        isLoadingDataset,
        fetchDataset,
        saveDatasets,
    };
});
