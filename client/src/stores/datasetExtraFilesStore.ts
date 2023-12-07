import { defineStore } from "pinia";

import { DatasetExtraFiles, fetchDatasetExtraFiles } from "@/api/datasets";
import { useSimpleStore } from "@/composables/simpleStore";

export const useDatasetExtraFilesStore = defineStore("datasetExtraFilesStore", () => {
    const { storedItems, getItemById, isLoadingItem, fetchItemById } = useSimpleStore<DatasetExtraFiles>((params) =>
        fetchDatasetExtraFiles({ dataset_id: params.id })
    );

    return {
        storedDatasetExtraFiles: storedItems,
        getDatasetExtraFiles: getItemById,
        isLoadingDatasetExtraFiles: isLoadingItem,
        fetchDatasetExtFilesByDatasetId: fetchItemById,
    };
});
