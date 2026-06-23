import { defineStore } from "pinia";

import type { DatasetTextContentDetails } from "@/api";
import { fetchDatasetTextContentDetails } from "@/api/datasets";
import { useKeyedCache } from "@/composables/keyedCache";

export const useDatasetTextContentStore = defineStore("datasetTextContentStore", () => {
    const { storedItems, getItemById, getItemLoadError, isLoadingItem, fetchItemById } =
        useKeyedCache<DatasetTextContentDetails>(fetchDatasetTextContentDetails);

    return {
        storedItems,
        getItemById,
        getItemLoadError,
        isLoadingItem,
        fetchItemById,
    };
});
