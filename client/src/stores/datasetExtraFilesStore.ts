import { defineStore } from "pinia";

import { GalaxyApi } from "@/api";
import { type DatasetExtraFiles } from "@/api/datasets";
import { type FetchParams, useKeyedCache } from "@/composables/keyedCache";
import { rethrowSimple } from "@/utils/simple-error";

export const useDatasetExtraFilesStore = defineStore("datasetExtraFilesStore", () => {
    async function fetchDatasetExtraFiles(params: FetchParams): Promise<DatasetExtraFiles> {
        const { data, error } = await GalaxyApi().GET("/api/datasets/{dataset_id}/extra_files", {
            params: { path: { dataset_id: params.id } },
        });
        if (error) {
            rethrowSimple(error);
        }
        return data;
    }

    const { storedItems, getItemById, isLoadingItem, fetchItemById } =
        useKeyedCache<DatasetExtraFiles>(fetchDatasetExtraFiles);

    return {
        storedDatasetExtraFiles: storedItems,
        getDatasetExtraFiles: getItemById,
        isLoadingDatasetExtraFiles: isLoadingItem,
        fetchDatasetExtFilesByDatasetId: fetchItemById,
    };
});
