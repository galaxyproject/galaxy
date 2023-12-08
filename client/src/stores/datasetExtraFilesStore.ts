import { defineStore } from "pinia";

import { DatasetExtraFiles, fetchDatasetExtraFiles } from "@/api/datasets";
import { useKeyedCache } from "@/composables/keyedCache";

export const useDatasetExtraFilesStore = defineStore("datasetExtraFilesStore", () => {
    const { storedItems, getItemById, isLoadingItem, fetchItemById } = useKeyedCache<DatasetExtraFiles>((params) =>
        fetchDatasetExtraFiles({ dataset_id: params.id })
    );

    return {
        storedDatasetExtraFiles: storedItems,
        getDatasetExtraFiles: getItemById,
        isLoadingDatasetExtraFiles: isLoadingItem,
        fetchDatasetExtFilesByDatasetId: fetchItemById,
    };
});
