import { defineStore } from "pinia";

import type { DatasetCollectionAttributes } from "@/api";
import { fetchCollectionAttributes } from "@/api/datasetCollections";
import { useKeyedCache } from "@/composables/keyedCache";

export const useCollectionAttributesStore = defineStore("collectionAttributesStore", () => {
    const { storedItems, getItemById, isLoadingItem, getItemLoadError } = useKeyedCache<DatasetCollectionAttributes>(
        (params) => fetchCollectionAttributes({ id: params.id, instance_type: "history" })
    );

    return {
        storedAttributes: storedItems,
        getAttributes: getItemById,
        isLoadingAttributes: isLoadingItem,
        getItemLoadError: getItemLoadError,
    };
});
