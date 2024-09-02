import { defineStore } from "pinia";

import type { DatasetCollectionAttributes } from "@/api";
import { fetchCollectionAttributes } from "@/api/datasetCollections";
import { useKeyedCache } from "@/composables/keyedCache";

export const useCollectionAttributesStore = defineStore("collectionAttributesStore", () => {
    const { storedItems, getItemById, isLoadingItem, hasItemLoadError } = useKeyedCache<DatasetCollectionAttributes>(
        (params) => fetchCollectionAttributes({ id: params.id, instance_type: "history" })
    );

    return {
        storedAttributes: storedItems,
        getAttributes: getItemById,
        isLoadingAttributes: isLoadingItem,
        hasItemLoadError: hasItemLoadError,
    };
});
