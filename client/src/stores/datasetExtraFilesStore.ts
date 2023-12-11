import { defineStore } from "pinia";
import { computed, del, ref, set } from "vue";

import { DatasetExtraFiles, fetchDatasetExtraFiles } from "@/api/datasets";

export const useDatasetExtraFilesStore = defineStore("datasetExtraFilesStore", () => {
    const storedDatasetExtraFiles = ref<{ [key: string]: DatasetExtraFiles }>({});
    const loading = ref<{ [key: string]: boolean }>({});

    const getDatasetExtraFiles = computed(() => {
        return (datasetId: string) => {
            const datasetExtFiles = storedDatasetExtraFiles.value[datasetId];
            if (!datasetExtFiles && !loading.value[datasetId]) {
                fetchDatasetExtFilesByDatasetId({ id: datasetId });
            }
            return datasetExtFiles ?? null;
        };
    });

    const isLoadingDatasetExtraFiles = computed(() => {
        return (datasetId: string) => {
            return loading.value[datasetId] ?? false;
        };
    });

    async function fetchDatasetExtFilesByDatasetId(params: { id: string }) {
        const datasetId = params.id;
        set(loading.value, datasetId, true);
        try {
            const { data: datasetExtFiles } = await fetchDatasetExtraFiles({
                dataset_id: datasetId,
            });
            set(storedDatasetExtraFiles.value, datasetId, datasetExtFiles);
            return datasetExtFiles;
        } finally {
            del(loading.value, datasetId);
        }
    }

    return {
        storedDatasetExtraFiles,
        getDatasetExtraFiles,
        isLoadingDatasetExtraFiles,
        fetchDatasetExtFilesByDatasetId,
    };
});
