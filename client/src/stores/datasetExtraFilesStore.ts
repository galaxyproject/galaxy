import { defineStore } from "pinia";

import { DatasetExtraFiles, fetchDatasetExtraFiles } from "@/api/datasets";
import { useSimpleKeyStore } from "@/composables/simpleKeyStore";

export const useDatasetExtraFilesStore = defineStore("datasetExtraFilesStore", () => {
    const { storedItems, getItemById, isLoadingItem, fetchItemById } = useSimpleKeyStore<DatasetExtraFiles>((params) =>
        fetchDatasetExtraFiles({ dataset_id: params.id })
    );

    return {
        storedDatasetExtraFiles: storedItems,
        getDatasetExtraFiles: getItemById,
        isLoadingDatasetExtraFiles: isLoadingItem,
        fetchDatasetExtFilesByDatasetId: fetchItemById,
    };
});
