import { defineStore } from "pinia";
import Vue, { computed, ref } from "vue";

import { DatasetEntry, HistoryContentItemBase } from "./services";
import { fetchDatasetDetails } from "./services/dataset.service";

export const useDatasetStore = defineStore("datasetStore", () => {
    const storedDatasets = ref<{ [key: string]: DatasetEntry }>({});

    const getDataset = computed(() => {
        return (datasetId: string) => {
            const dataset = storedDatasets.value[datasetId];
            if (needsUpdate(dataset)) {
                fetchDataset({ id: datasetId });
            }
            return dataset ?? null;
        };
    });

    async function fetchDataset(params: { id: string }) {
        const dataset = await fetchDatasetDetails(params);
        Vue.set(storedDatasets.value, dataset.id, dataset);
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
        fetchDataset,
        saveDatasets,
    };
});
